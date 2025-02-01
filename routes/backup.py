from flask import Blueprint, jsonify, current_app, request
import os
import shutil
from datetime import datetime
import subprocess
from models import db, Backup, AuditTrail
from services.auth_services import admin_required, log_audit_trail
import uuid
import platform
import traceback
import tarfile
import tempfile
import lzma
from sqlalchemy import text
from enum import Enum
from flask_jwt_extended import get_jwt_identity
import hashlib
import time

backup = Blueprint('backup', __name__)

class BackupType(Enum):
    FULL = 'FULL'
    INCREMENTAL = 'INCR'

def generate_backup_id(backup_type):
    # Format: BK_FULL_YYYYMMDD_HHMMSS or BK_INCR_YYYYMMDD_HHMMSS
    timestamp = datetime.now().strftime(f'BK_{backup_type.value}_%Y%m%d_%H%M%S')
    return timestamp

def get_changed_files(directory, last_backup_date=None):
    """Get list of files modified since last backup"""
    changed_files = []
    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if last_backup_date is None or file_mtime > last_backup_date:
                changed_files.append(filepath)
    return changed_files

@backup.route('/create/<backup_type>', methods=['POST'])
@admin_required
def create_backup(backup_type):
    try:
        backup_type = BackupType(backup_type.upper())
        backup_id = generate_backup_id(backup_type)
        
        # Create backup directories
        backup_dir = os.path.join('backups', backup_id)
        db_backup_dir = os.path.join(backup_dir, 'database')
        files_backup_dir = os.path.join(backup_dir, 'files')
        
        os.makedirs(db_backup_dir, exist_ok=True)
        os.makedirs(files_backup_dir, exist_ok=True)

        # Get database connection details
        db_url = current_app.config['SQLALCHEMY_DATABASE_URI']
        db_parts = db_url.replace('postgresql://', '').split('/')
        db_name = db_parts[1].split('?')[0]
        credentials = db_parts[0].split('@')[0]
        db_user = credentials.split(':')[0]
        db_pass = credentials.split(':')[1]
        host = db_parts[0].split('@')[1].split(':')[0]

        os.environ['PGPASSWORD'] = db_pass

        try:
            pg_bin = current_app.config.get('PG_BIN')
            if not pg_bin:
                raise Exception("PostgreSQL binary directory not found")

            if backup_type == BackupType.FULL:
                # Use pg_basebackup for full backup with WAL
                pg_basebackup_exe = os.path.join(
                    pg_bin, 
                    'pg_basebackup.exe' if platform.system() == 'Windows' else 'pg_basebackup'
                )
                # We expect pg_basebackup to write a tar archive file named "base.backup"
                backup_command = f'"{pg_basebackup_exe}" -h {host} -U {db_user} -D "{db_backup_dir}" -Ft -z -Xs'
                print(f"Executing full backup command: {backup_command}")
                result = subprocess.run(backup_command, shell=True, capture_output=True, text=True)
                
                if result.returncode != 0:
                    raise Exception(f"Full backup failed: {result.stderr}")
                
            else:  # Incremental backup
                # Get last full backup
                last_full = Backup.query.filter_by(backup_type=BackupType.FULL.value)\
                                    .order_by(Backup.backup_date.desc())\
                                    .first()
                if not last_full:
                    raise Exception("No full backup found. Please create a full backup first")

                # Use pg_receivewal to capture WAL changes since last backup.
                # (In this "fixed" code we assume that later you update your incremental routine
                # to produce a dump file named "database.backup" so that pg_restore can use it.)
                pg_receivewal_exe = os.path.join(
                    pg_bin, 
                    'pg_receivewal.exe' if platform.system() == 'Windows' else 'pg_receivewal'
                )
                wal_dir = os.path.join(db_backup_dir, 'wal')
                os.makedirs(wal_dir, exist_ok=True)

                last_backup = Backup.query.order_by(Backup.backup_date.desc()).first()
                start_lsn = last_backup.wal_lsn if last_backup else None

                backup_command = f'"{pg_receivewal_exe}" -h {host} -U {db_user} -D "{wal_dir}" ' \
                                f'--start-lsn {start_lsn if start_lsn else "0/0"} -n'
                print(f"Executing incremental backup command: {backup_command}")
                result = subprocess.run(backup_command, shell=True, capture_output=True, text=True)
                
                if result.returncode != 0:
                    raise Exception(f"Incremental backup failed: {result.stderr}")

                # Get current WAL location for next backup
                current_lsn = get_current_wal_lsn(pg_bin, host, db_user, db_name)

            # Backup repository files
            repository_dir = 'research_repository'
            archive_path = os.path.join(files_backup_dir, 'repository_backup.tar.xz')
            
            if os.path.exists(repository_dir):
                if backup_type == BackupType.FULL:
                    # Full backup of all files
                    with tarfile.open(archive_path, "w:xz") as tar:
                        tar.add(repository_dir, arcname=os.path.basename(repository_dir))
                else:
                    # Incremental backup of changed files only
                    last_full = Backup.query.filter_by(backup_type=BackupType.FULL.value)\
                                        .order_by(Backup.backup_date.desc())\
                                        .first()
                    if not last_full:
                        raise Exception("No full backup found. Please create a full backup first")
                    changed_files = get_changed_files(repository_dir, last_full.backup_date)
                    
                    with tarfile.open(archive_path, "w:xz") as tar:
                        for filepath in changed_files:
                            arcname = os.path.relpath(filepath, start=os.path.dirname(repository_dir))
                            tar.add(filepath, arcname=arcname)

            # Calculate total size
            total_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(backup_dir)
                for filename in filenames
            )

            new_backup = Backup(
                backup_id=backup_id,
                backup_type=backup_type.value,
                backup_date=datetime.now(),
                database_backup_location=db_backup_dir,
                files_backup_location=files_backup_dir,
                total_size=total_size,
                parent_backup_id=last_full.backup_id if backup_type == BackupType.INCREMENTAL else None,
                wal_lsn=current_lsn if backup_type == BackupType.INCREMENTAL else None
            )
            
            db.session.add(new_backup)
            db.session.commit()

            log_audit_trail(
                user_id=get_jwt_identity(),
                operation="CREATE_BACKUP",
                action_desc=f"Created {backup_type.value} backup with ID: {backup_id}",
                table_name="backup",
                record_id=backup_id
            )

            return jsonify({
                'message': f'{backup_type.value} backup created successfully',
                'backup_id': backup_id
            }), 201

        finally:
            os.environ.pop('PGPASSWORD', None)

    except Exception as e:
        print(f"Error during backup: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        if 'backup_dir' in locals() and os.path.exists(backup_dir):
            shutil.rmtree(backup_dir, ignore_errors=True)
        return jsonify({'error': str(e)}), 500

@backup.route('/restore/<backup_id>', methods=['POST'])
@admin_required
def restore_backup(backup_id):
    restore_successful = False
    service_name = None
    original_data_backup = None
    try:
        # Remove any active SQLAlchemy sessions
        db.session.remove()

        # Get backup information BEFORE stopping PostgreSQL
        target_backup = Backup.query.filter_by(backup_id=backup_id).first()
        if not target_backup:
            return jsonify({'error': 'Backup not found'}), 404

        # Store necessary information
        backup_info = {
            'database_backup_location': target_backup.database_backup_location,
            'files_backup_location': target_backup.files_backup_location,
            'backup_type': target_backup.backup_type
        }
        user_id = get_jwt_identity()

        if target_backup.backup_type != BackupType.FULL.value:
            raise Exception("Incremental restore is not implemented in this fix.")

        # --- SERVICE CONTROL: Stop PostgreSQL ---
        if platform.system() == 'Windows':
            # Find PostgreSQL service name
            list_command = 'sc query state= all | findstr /I "postgresql"'
            result = subprocess.run(list_command, shell=True, capture_output=True, text=True)
            service_output = result.stdout.lower()
            if 'postgresql-x64-15' in service_output:
                service_name = 'postgresql-x64-15'
            elif 'postgresql-15' in service_output:
                service_name = 'postgresql-15'
            elif 'postgresql' in service_output:
                service_name = 'postgresql'
            else:
                raise Exception("Could not find PostgreSQL service name")
            print(f"Found PostgreSQL service: {service_name}")

            # Save backup records before stopping service
            backup_records = []
            try:
                backup_records = [{
                    'backup_id': b.backup_id,
                    'backup_type': b.backup_type,
                    'backup_date': b.backup_date.isoformat(),
                    'database_backup_location': b.database_backup_location,
                    'files_backup_location': b.files_backup_location,
                    'total_size': b.total_size,
                    'parent_backup_id': b.parent_backup_id,
                    'wal_lsn': b.wal_lsn
                } for b in Backup.query.all()]
            except Exception as e:
                print(f"Warning: Could not preserve backup records: {e}")

            # Stop the service
            stop_command = f'net stop {service_name}'
            try:
                subprocess.run(stop_command, shell=True, check=True, capture_output=True)
                time.sleep(10)
                status_command = f'sc query {service_name}'
                status_result = subprocess.run(status_command, shell=True, capture_output=True, text=True)
                if "STOPPED" not in status_result.stdout.upper():
                    raise Exception(f"Failed to stop PostgreSQL service. Current status: {status_result.stdout}")
                print("PostgreSQL service stopped successfully")
            except subprocess.CalledProcessError as e:
                raise Exception(f"Failed to stop PostgreSQL service: {e.stderr.decode().strip() if e.stderr else 'Access denied'}")

            # --- PHYSICAL RESTORE PROCEDURE ---
            pgdata = current_app.config.get('PGDATA')
            if not pgdata:
                raise Exception("PGDATA not configured for restore.")

            # Backup current data directory before removing it
            if os.path.exists(pgdata):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                original_data_backup = f"{pgdata}_backup_{timestamp}"
                print(f"Backing up current data directory to: {original_data_backup}")
                shutil.copytree(pgdata, original_data_backup)
                shutil.rmtree(pgdata)
            os.makedirs(pgdata)

            try:
                # Extract the backup
                base_backup_file = os.path.join(backup_info['database_backup_location'], 'base.tar.gz')
                if not os.path.exists(base_backup_file):
                    raise Exception(f"Backup file not found: {base_backup_file}")

                with tarfile.open(base_backup_file, "r:gz") as tar:
                    tar.extractall(path=pgdata)
                print(f"Extracted backup from {base_backup_file}")

                # Create recovery.signal file
                recovery_signal_path = os.path.join(pgdata, 'recovery.signal')
                with open(recovery_signal_path, 'w') as f:
                    pass
                print("Created recovery.signal file")

                # Update recovery configuration
                recovery_conf_path = os.path.join(pgdata, 'postgresql.auto.conf')
                with open(recovery_conf_path, 'a') as f:
                    f.write("\n# Recovery configuration\n")
                    f.write("restore_command = ''\n")
                    f.write("recovery_target_timeline = 'latest'\n")
                print("Updated recovery configuration")

                # Set proper permissions
                subprocess.run(f'icacls "{pgdata}" /reset', shell=True, check=True)
                subprocess.run(f'icacls "{pgdata}" /grant "NT AUTHORITY\\NetworkService":(OI)(CI)F /T', shell=True, check=True)
                subprocess.run(f'icacls "{pgdata}" /grant "NT AUTHORITY\\SYSTEM":(OI)(CI)F /T', shell=True, check=True)
                subprocess.run(f'icacls "{pgdata}" /grant "BUILTIN\\Administrators":(OI)(CI)F /T', shell=True, check=True)
                print("Set permissions on PGDATA directory")

                # Start PostgreSQL service
                start_command = f'net start {service_name}'
                subprocess.run(start_command, shell=True, check=True, capture_output=True)
                time.sleep(15)

                # Verify service started
                status_command = f'sc query {service_name}'
                status_result = subprocess.run(status_command, shell=True, capture_output=True, text=True)
                if "RUNNING" not in status_result.stdout.upper():
                    raise Exception("Failed to start PostgreSQL service")

                print("PostgreSQL service started successfully")
                restore_successful = True

            except Exception as e:
                # If anything fails during restore, restore the original data directory
                if original_data_backup and os.path.exists(original_data_backup):
                    print("Restore failed. Restoring original data directory...")
                    if os.path.exists(pgdata):
                        shutil.rmtree(pgdata)
                    shutil.copytree(original_data_backup, pgdata)
                    
                    # Try to start PostgreSQL with original data
                    try:
                        subprocess.run(f'net start {service_name}', shell=True, check=True)
                        print("Restored original data directory and restarted PostgreSQL")
                    except Exception as start_error:
                        print(f"Failed to restart PostgreSQL with original data: {start_error}")
                
                raise Exception(f"Restore failed: {str(e)}")

            finally:
                # Clean up backup of original data directory
                if original_data_backup and os.path.exists(original_data_backup):
                    try:
                        shutil.rmtree(original_data_backup)
                    except Exception as e:
                        print(f"Warning: Could not remove temporary backup: {e}")

        if restore_successful:
            return jsonify({
                'message': 'Backup restored successfully',
                'backup_id': backup_id
            }), 200
        else:
            return jsonify({
                'error': 'Restore failed. Original data has been restored.'
            }), 500

    except Exception as e:
        print(f"Error during restore: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

@backup.route('/list', methods=['GET'])
@admin_required
def list_backups():
    try:
        backups = Backup.query.order_by(Backup.backup_date.desc()).all()
        return jsonify({
            'backups': [{
                'backup_id': b.backup_id,
                'backup_date': b.backup_date.isoformat(),
                'backup_type': b.backup_type,
                'database_backup_location': os.path.basename(b.database_backup_location),
                'files_backup_location': os.path.basename(b.files_backup_location),
                'total_size': b.total_size
            } for b in backups]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_current_wal_lsn(pg_bin, host, db_user, db_name):
    """Get current WAL LSN position"""
    psql_exe = os.path.join(
        pg_bin, 
        'psql.exe' if platform.system() == 'Windows' else 'psql'
    )
    query = "SELECT pg_current_wal_lsn()::text;"
    
    result = subprocess.run(
        f'"{psql_exe}" -h {host} -U {db_user} -d {db_name} -t -A -c "{query}"',
        shell=True, capture_output=True, text=True
    )
    
    if result.returncode != 0:
        raise Exception(f"Failed to get WAL LSN: {result.stderr}")
    
    return result.stdout.strip()
