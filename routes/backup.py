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

backup = Blueprint('backup', __name__)

class BackupType(Enum):
    FULL = 'FULL'
    INCREMENTAL = 'INCREMENTAL'

def generate_backup_id(backup_type):
    # Format: BK_FULL_YYYYMMDD_HHMMSS or BK_INCR_YYYYMMDD_HHMMSS
    timestamp = datetime.now().strftime(f'BK_{backup_type.value}_%Y%m%d_%H%M%S')
    return timestamp

@backup.route('/create/<backup_type>', methods=['POST'])
@admin_required
def create_backup(backup_type):
    try:
        # Validate backup type
        try:
            backup_type = BackupType(backup_type.upper())
        except ValueError:
            return jsonify({'error': 'Invalid backup type. Use FULL or INCREMENTAL'}), 400

        # Generate backup ID
        backup_id = generate_backup_id(backup_type)
        
        # Create backup directories using relative paths
        backup_dir = os.path.join('backups', backup_id)
        db_backup_dir = os.path.join(backup_dir, 'database')
        files_backup_dir = os.path.join(backup_dir, 'files')
        
        print(f"Creating directories: {db_backup_dir}, {files_backup_dir}")
        os.makedirs(db_backup_dir, exist_ok=True)
        os.makedirs(files_backup_dir, exist_ok=True)

        # Get PostgreSQL bin directory from config
        pg_bin = current_app.config.get('PG_BIN')
        if not pg_bin:
            print("PostgreSQL binary directory not found")
            raise Exception("PostgreSQL binary directory not found. Please configure PG_BIN in config.py")

        # Get database connection details
        db_url = current_app.config['SQLALCHEMY_DATABASE_URI']
        db_parts = db_url.replace('postgresql://', '').split('/')
        db_name = db_parts[1].split('?')[0]  # Remove any query parameters
        credentials = db_parts[0].split('@')[0]
        db_user = credentials.split(':')[0]
        db_pass = credentials.split(':')[1].split('@')[0]
        host = db_parts[0].split('@')[1].split(':')[0]

        # Set PGPASSWORD environment variable
        os.environ['PGPASSWORD'] = db_pass

        try:
            # Get last full backup for incremental
            last_full = None
            if backup_type == BackupType.INCREMENTAL:
                last_full = Backup.query.filter_by(backup_type=BackupType.FULL.value)\
                                    .order_by(Backup.backup_date.desc())\
                                    .first()
                if not last_full:
                    return jsonify({'error': 'No full backup found. Please create a full backup first'}), 400

            # Backup database using pg_dump
            db_backup_path = os.path.join(db_backup_dir, 'database.backup')
            pg_dump_exe = os.path.join(pg_bin, 'pg_dump.exe' if platform.system() == 'Windows' else 'pg_dump')
            
            # Create backup command based on type
            if backup_type == BackupType.FULL:
                pg_dump_command = f'"{pg_dump_exe}" -h {host} -U {db_user} -d {db_name} -Fc -f "{db_backup_path}"'
            else:
                # For incremental, we'll still do a full backup but only of the data that changed
                # You might want to implement a more sophisticated incremental backup strategy
                pg_dump_command = f'"{pg_dump_exe}" -h {host} -U {db_user} -d {db_name} -Fc -f "{db_backup_path}"'
            
            print(f"Executing command: {pg_dump_command}")
            result = subprocess.run(pg_dump_command, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"pg_dump error: {result.stderr}")
                raise Exception(f"Database backup failed: {result.stderr}")
            
            print("Database backup completed successfully")

        finally:
            # Clear PGPASSWORD environment variable
            os.environ.pop('PGPASSWORD', None)

        # Create tar.xz archive for repository files
        repository_dir = 'research_repository'
        archive_path = os.path.join(files_backup_dir, 'repository_backup.tar.xz')
        
        print(f"Creating compressed archive of {repository_dir}")
        if os.path.exists(repository_dir):
            with tarfile.open(archive_path, "w:xz", preset=9) as tar:
                tar.add(repository_dir, arcname=os.path.basename(repository_dir))
        else:
            print(f"Warning: Repository directory {repository_dir} does not exist")
            with tarfile.open(archive_path, "w:xz") as tar:
                pass

        # Calculate total size
        total_size = sum(os.path.getsize(os.path.join(dirpath, filename))
            for dirpath, dirnames, filenames in os.walk(backup_dir)
            for filename in filenames)

        # Create backup record in database
        new_backup = Backup(
            backup_id=backup_id,
            backup_type=backup_type.value,
            backup_date=datetime.now(),
            database_backup_location=db_backup_dir,
            files_backup_location=files_backup_dir,
            total_size=total_size,
            parent_backup_id=last_full.backup_id if backup_type == BackupType.INCREMENTAL else None
        )
        
        db.session.add(new_backup)
        db.session.commit()

        # Use auth_services audit trail
        log_audit_trail(
            user_id=get_jwt_identity(),
            operation="CREATE",
            action_desc=f"Created {backup_type.value} backup with ID: {backup_id}",
            table_name="backup",
            record_id=backup_id
        )

        return jsonify({
            'message': f'{backup_type.value} backup created successfully',
            'backup_id': backup_id
        }), 201

    except Exception as e:
        print(f"Error during {backup_type.value} backup: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        if 'backup_dir' in locals() and os.path.exists(backup_dir):
            shutil.rmtree(backup_dir, ignore_errors=True)
        return jsonify({'error': str(e)}), 500

@backup.route('/restore/<backup_id>', methods=['POST'])
@admin_required
def restore_backup(backup_id):
    try:
        # Get the target backup record
        target_backup = Backup.query.filter_by(backup_id=backup_id).first()
        if not target_backup:
            return jsonify({'error': 'Backup not found'}), 404
        else:
            # For full backup, we just need the single backup
            backup_chain = [target_backup]

        print(f"Restore chain: {[b.backup_id for b in backup_chain]}")

        # Store current audit logs and backup records
        print("Storing current audit logs and backup records")
        audit_logs = db.session.query(AuditTrail).all()
        backup_records = db.session.query(Backup).all()

        # Get database connection details
        db_url = current_app.config['SQLALCHEMY_DATABASE_URI']
        db_parts = db_url.replace('postgresql://', '').split('/')
        db_name = db_parts[1].split('?')[0]
        credentials = db_parts[0].split('@')[0]
        db_user = credentials.split(':')[0]
        db_pass = credentials.split(':')[1].split('@')[0]
        host = db_parts[0].split('@')[1].split(':')[0]

        # Close existing connections
        db.session.close()
        db.engine.dispose()

        # Set PGPASSWORD environment variable
        os.environ['PGPASSWORD'] = db_pass

        try:
            pg_bin = current_app.config.get('PG_BIN')
            if not pg_bin:
                raise Exception("PostgreSQL binary directory not found")

            pg_restore_exe = os.path.join(pg_bin, 'pg_restore.exe' if platform.system() == 'Windows' else 'pg_restore')
            psql_exe = os.path.join(pg_bin, 'psql.exe' if platform.system() == 'Windows' else 'psql')

            # Terminate existing connections and recreate database
            print("Preparing database for restore")
            terminate_command = f'"{psql_exe}" -h {host} -U {db_user} -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = \'{db_name}\' AND pid <> pg_backend_pid();"'
            subprocess.run(terminate_command, shell=True, check=True)

            drop_command = f'"{psql_exe}" -h {host} -U {db_user} -d postgres -c "DROP DATABASE IF EXISTS {db_name};"'
            create_command = f'"{psql_exe}" -h {host} -U {db_user} -d postgres -c "CREATE DATABASE {db_name};"'
            
            subprocess.run(drop_command, shell=True, check=True)
            subprocess.run(create_command, shell=True, check=True)

            # Restore each backup in the chain
            for backup in backup_chain:
                print(f"Restoring {backup.backup_type} backup: {backup.backup_id}")
                db_backup_file = os.path.join(backup.database_backup_location, 'database.backup')
                
                if backup.backup_type == BackupType.FULL.value:
                    # For full backup, use regular restore
                    restore_command = f'"{pg_restore_exe}" -h {host} -U {db_user} -d {db_name} "{db_backup_file}"'
                else:
                    # For incremental, apply changes
                    restore_command = f'"{pg_restore_exe}" -h {host} -U {db_user} -d {db_name} --data-only "{db_backup_file}"'
                
                result = subprocess.run(restore_command, shell=True, capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"Restore error: {result.stderr}")
                    raise Exception(f"Database restore failed for {backup.backup_id}: {result.stderr}")

            # Restore files from the target backup
            archive_path = os.path.join(target_backup.files_backup_location, 'repository_backup.tar.xz')
            if os.path.exists(archive_path):
                repository_dir = 'research_repository'
                if os.path.exists(repository_dir):
                    shutil.rmtree(repository_dir)
                
                print(f"Extracting files from {archive_path}")
                with tarfile.open(archive_path, "r:xz") as tar:
                    tar.extractall(path=os.path.dirname(repository_dir))

            # Reinsert audit logs and backup records
            print("Restoring audit logs and backup records")
            for log in audit_logs:
                db.session.merge(log)
            for backup in backup_records:
                db.session.merge(backup)

            # Add audit log for restore operation
            audit_entry = AuditTrail(
                user_id=get_jwt_identity(),
                action="RESTORE_BACKUP",
                details=f"Restored backup chain ending with ID: {backup_id}"
            )
            db.session.add(audit_entry)
            db.session.commit()

            return jsonify({'message': 'Backup restored successfully'}), 200

        finally:
            os.environ.pop('PGPASSWORD', None)

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
                'database_backup_location': os.path.basename(b.database_backup_location),  # Just the folder name
                'files_backup_location': os.path.basename(b.files_backup_location),  # Just the folder name
                'total_size': b.total_size
            } for b in backups]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500 