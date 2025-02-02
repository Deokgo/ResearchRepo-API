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
from sqlalchemy import create_engine

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
                # Default PostgreSQL binary location on Windows
                pg_bin = r'C:\Program Files\PostgreSQL\15\bin'
            print(f"Using PostgreSQL binaries from: {pg_bin}")

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

                # Create WAL archive directory
                wal_dir = os.path.join(db_backup_dir, 'wal')
                os.makedirs(wal_dir, exist_ok=True)

                # Get current WAL location
                current_lsn = get_current_wal_lsn(pg_bin, host, db_user, db_name)
                print(f"Current WAL LSN: {current_lsn}")

                # Get last backup's LSN
                last_lsn = last_full.wal_lsn or '0/0'
                print(f"Last backup LSN: {last_lsn}")

                # Use pg_receivewal to get WAL files
                pg_receivewal_exe = os.path.join(
                    pg_bin, 
                    'pg_receivewal.exe' if platform.system() == 'Windows' else 'pg_receivewal'
                )

                # Archive WAL files since last backup
                archive_command = f'"{pg_receivewal_exe}" -h {host} -U {db_user} ' \
                                f'--directory="{wal_dir}" ' \
                                f'--start-lsn={last_lsn} ' \
                                f'--stop-lsn={current_lsn} ' \
                                f'--verbose'

                print(f"Executing incremental backup command: {archive_command}")
                result = subprocess.run(archive_command, shell=True, capture_output=True, text=True)
                
                if result.returncode != 0:
                    raise Exception(f"Incremental backup failed: {result.stderr}")

                # Compress the WAL files
                wal_archive = os.path.join(db_backup_dir, 'wal_archive.tar.gz')
                with tarfile.open(wal_archive, "w:gz") as tar:
                    tar.add(wal_dir, arcname=os.path.basename(wal_dir))

                # Create backup.info file with metadata
                backup_info_path = os.path.join(db_backup_dir, 'backup.info')
                with open(backup_info_path, 'w') as f:
                    f.write(f"backup_id={backup_id}\n")
                    f.write(f"backup_type={backup_type.value}\n")
                    f.write(f"parent_backup_id={last_full.backup_id}\n")
                    f.write(f"start_wal_location={last_lsn}\n")
                    f.write(f"end_wal_location={current_lsn}\n")
                    f.write(f"backup_date={datetime.now().isoformat()}\n")

                # Also backup changed repository files
                repository_dir = 'research_repository'
                archive_path = os.path.join(files_backup_dir, 'repository_backup.tar.xz')
                
                if os.path.exists(repository_dir):
                    # Incremental backup of changed files only
                    changed_files = get_changed_files(repository_dir, last_full.backup_date)
                    if changed_files:  # Only create archive if there are changes
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
        db.engine.dispose()

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

            # Convert path to proper Windows format
            pgdata = pgdata.replace('/', '\\')
            
            # Backup current data directory before removing it
            if os.path.exists(pgdata):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                original_data_backup = f"{pgdata}_backup_{timestamp}"
                print(f"Backing up current data directory to: {original_data_backup}")
                shutil.copytree(pgdata, original_data_backup)
                shutil.rmtree(pgdata)
            os.makedirs(pgdata)

            try:
                # Create a logs directory in an accessible location
                logs_dir = os.path.join(os.getcwd(), 'postgresql_logs')
                if not os.path.exists(logs_dir):
                    os.makedirs(logs_dir)
                print(f"Created logs directory: {logs_dir}")

                # Update postgresql.conf with absolute path for logs
                postgresql_conf = os.path.join(pgdata, 'postgresql.conf')
                # Convert path to proper format for PostgreSQL
                postgres_log_path = logs_dir.replace('\\', '/')
                
                log_config = (
                    "\n# Enhanced logging configuration\n"
                    "log_destination = 'stderr'\n"
                    "logging_collector = on\n"
                    f"log_directory = '{postgres_log_path}'\n"
                    "log_filename = 'postgresql.log'\n"  # Single log file
                    "log_rotation_age = 0\n"  # Disable automatic rotation
                    "log_truncate_on_rotation = off\n"
                    "log_min_messages = debug1\n"
                    "log_min_error_statement = debug1\n"
                    "log_min_duration_statement = 0\n"
                    "log_connections = on\n"
                    "log_disconnections = on\n"
                    "log_duration = on\n"
                    "log_line_prefix = '%m [%p] %q%u@%d '\n"
                )

                # Try a different restore approach
                try:
                    # Get PostgreSQL binary directory from config
                    pg_bin = current_app.config.get('PG_BIN')
                    if not pg_bin:
                        # Default PostgreSQL binary location on Windows
                        pg_bin = r'C:\Program Files\PostgreSQL\15\bin'
                    print(f"Using PostgreSQL binaries from: {pg_bin}")

                    # First, stop PostgreSQL and clean data directory
                    if os.path.exists(pgdata):
                        shutil.rmtree(pgdata)
                    os.makedirs(pgdata)

                    # Extract backup
                    base_backup_file = os.path.join(backup_info['database_backup_location'], 'base.tar.gz')
                    if not os.path.exists(base_backup_file):
                        raise Exception(f"Backup file not found: {base_backup_file}")

                    print("Extracting backup...")
                    with tarfile.open(base_backup_file, "r:gz") as tar:
                        tar.extractall(path=pgdata)

                    # Run pg_resetwal to reset the WAL
                    pg_resetwal_exe = os.path.join(
                        pg_bin, 
                        'pg_resetwal.exe' if platform.system() == 'Windows' else 'pg_resetwal'
                    )
                    reset_command = f'"{pg_resetwal_exe}" -f "{pgdata}"'
                    print(f"Running pg_resetwal: {reset_command}")
                    result = subprocess.run(reset_command, shell=True, capture_output=True, text=True)
                    if result.returncode != 0:
                        print(f"pg_resetwal error: {result.stderr}")
                        raise Exception("Failed to reset WAL")
                    print(f"pg_resetwal output: {result.stdout}")

                    # Create minimal postgresql.conf
                    with open(postgresql_conf, 'w') as f:
                        f.write(log_config)
                        f.write("\n# Basic configuration\n")
                        f.write("listen_addresses = '*'\n")
                        f.write("port = 5432\n")
                        f.write("max_connections = 100\n")
                        f.write("shared_buffers = 128MB\n")
                        f.write("dynamic_shared_memory_type = windows\n")
                        f.write("max_wal_size = 1GB\n")
                        f.write("min_wal_size = 80MB\n")
                        f.write("wal_level = replica\n")
                        f.write("archive_mode = off\n")

                    # Remove any existing recovery files
                    recovery_files = ['recovery.signal', 'backup_label', 'postgresql.auto.conf']
                    for file in recovery_files:
                        file_path = os.path.join(pgdata, file)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            print(f"Removed {file}")

                    # Ensure pg_wal directory exists
                    pg_wal_dir = os.path.join(pgdata, 'pg_wal')
                    if not os.path.exists(pg_wal_dir):
                        os.makedirs(pg_wal_dir)
                    print("Created pg_wal directory")

                    # Set permissions
                    for root, dirs, files in os.walk(pgdata):
                        for d in dirs:
                            os.chmod(os.path.join(root, d), 0o700)
                        for f in files:
                            os.chmod(os.path.join(root, f), 0o600)


                    # Try to start PostgreSQL
                    start_command = f'net start postgresql-x64-15'
                    result = subprocess.run(start_command, shell=True, capture_output=True, text=True)
                    print(f"Start command output: {result.stdout}")
                    
                    # Increase initial wait time after service start
                    time.sleep(15)  # Increased from 10 to 15 seconds

                    # Test connection and return response
                    try:
                        # Create a new connection to test with retries
                        max_retries = 5  # Increased from 3 to 5
                        retry_delay = 10  # Increased from 5 to 10 seconds
                        
                        connection_success = False
                        for attempt in range(max_retries):
                            try:
                                # Test connection
                                test_engine = create_engine(
                                    current_app.config['SQLALCHEMY_DATABASE_URI'],
                                    pool_pre_ping=True,  # Add connection validation
                                    pool_timeout=30  # Increase timeout
                                )
                                with test_engine.connect() as conn:
                                    # Run a simple query to verify connection
                                    conn.execute(text("SELECT 1"))
                                test_engine.dispose()
                                
                                # If we get here, connection is successful
                                connection_success = True
                                print(f"Database connection successful on attempt {attempt + 1}")
                                
                                # Wait longer before attempting to log
                                time.sleep(5)
                                
                                # Add specific retries for audit trail logging
                                audit_max_retries = 3
                                audit_retry_delay = 5
                                audit_success = False
                                
                                for audit_attempt in range(audit_max_retries):
                                    try:
                                        # Create fresh database session for audit logging
                                        db.session.remove()
                                        db.session.close()
                                        db.engine.dispose()
                                        
                                        # Try to log audit trail
                                        log_audit_trail(
                                            user_id=user_id,
                                            operation="RESTORE_BACKUP",
                                            action_desc=f"Restored backup with ID: {backup_id}",
                                            table_name="backup",
                                            record_id=backup_id
                                        )
                                        print("Audit trail logged successfully")
                                        audit_success = True
                                        break
                                    except Exception as audit_error:
                                        print(f"Audit logging attempt {audit_attempt + 1}/{audit_max_retries} failed: {str(audit_error)}")
                                        if audit_attempt < audit_max_retries - 1:
                                            time.sleep(audit_retry_delay)
                                            continue
                                
                                if not audit_success:
                                    print("Warning: All audit logging attempts failed")
                                
                                break

                            except Exception as e:
                                print(f"Connection attempt {attempt + 1}/{max_retries} failed: {str(e)}")
                                if attempt < max_retries - 1:
                                    time.sleep(retry_delay)
                                    continue
                                else:
                                    raise Exception("Failed to establish database connection after maximum retries")

                        if connection_success:
                            return jsonify({
                                'message': 'Backup restored successfully',
                                'backup_id': backup_id,
                                'audit_log': 'Warning: Audit log may have failed' if not connection_success else 'Success'
                            }), 200
                        else:
                            return jsonify({
                                'error': 'Restore completed but database connection failed'
                            }), 500

                    except Exception as e:
                        return jsonify({
                            'error': 'Restore completed but database connection failed'
                        }), 500

                except Exception as e:
                    print(f"Error during restore: {str(e)}")
                    return jsonify({'error': str(e)}), 500

            except Exception as e:
                # If anything fails during restore, restore the original data directory
                if original_data_backup and os.path.exists(original_data_backup):
                    print("Restore failed. Restoring original data directory...")
                    if os.path.exists(pgdata):
                        shutil.rmtree(pgdata)
                    shutil.copytree(original_data_backup, pgdata)
                    
                    # Try to start PostgreSQL with original data
                    try:
                        subprocess.run('net start postgresql-x64-15', shell=True, check=True)
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
