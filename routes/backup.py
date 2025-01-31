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
        db_pass = credentials.split(':')[1].split('@')[0]
        host = db_parts[0].split('@')[1].split(':')[0]

        os.environ['PGPASSWORD'] = db_pass

        try:
            pg_bin = current_app.config.get('PG_BIN')
            if not pg_bin:
                raise Exception("PostgreSQL binary directory not found")

            if backup_type == BackupType.FULL:
                # Use pg_dump for full backup
                pg_dump_exe = os.path.join(pg_bin, 'pg_dump.exe' if platform.system() == 'Windows' else 'pg_dump')
                db_backup_file = os.path.join(db_backup_dir, 'database.backup')
                
                # Create full backup using pg_dump
                backup_command = f'"{pg_dump_exe}" -h {host} -U {db_user} -d {db_name} -Fc -f "{db_backup_file}"'
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

                pg_dump_exe = os.path.join(pg_bin, 'pg_dump.exe' if platform.system() == 'Windows' else 'pg_dump')
                db_backup_file = os.path.join(db_backup_dir, 'database.backup')

                # Get timestamp of last backup
                last_backup_date = last_full.backup_date.strftime('%Y-%m-%d %H:%M:%S')

                # Backup only schema and data from tables that have been modified
                backup_command = f'"{pg_dump_exe}" -h {host} -U {db_user} -d {db_name} ' \
                               '--data-only ' \
                               '--exclude-table-data=audit_trail ' \
                               '--exclude-table-data=backup ' \
                               '-Fc -f "{db_backup_file}"'

                print(f"Executing incremental backup command: {backup_command}")
                result = subprocess.run(backup_command, shell=True, capture_output=True, text=True)
                
                if result.returncode != 0:
                    raise Exception(f"Incremental backup failed: {result.stderr}")

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

                    # Get files modified since last backup
                    changed_files = get_changed_files(repository_dir, last_full.backup_date)
                    
                    if changed_files:
                        with tarfile.open(archive_path, "w:xz") as tar:
                            for filepath in changed_files:
                                # Store files with their relative paths
                                arcname = os.path.relpath(filepath, start=os.path.dirname(repository_dir))
                                tar.add(filepath, arcname=arcname)
                    else:
                        # Create empty archive if no changes
                        with tarfile.open(archive_path, "w:xz") as tar:
                            pass

            # Calculate total size
            total_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(backup_dir)
                for filename in filenames)

            # Create backup record
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

            # Log audit trail
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
    try:
        # Get the target backup record
        target_backup = Backup.query.filter_by(backup_id=backup_id).first()
        if not target_backup:
            return jsonify({'error': 'Backup not found'}), 404

        # Get the chain of backups needed for restore
        backup_chain = []
        if target_backup.backup_type == BackupType.INCREMENTAL.value:
            # Find the full backup and all incremental backups up to the target
            current_backup = target_backup
            while current_backup:
                backup_chain.insert(0, current_backup)  # Insert at start to maintain order
                if current_backup.backup_type == BackupType.FULL.value:
                    break
                current_backup = Backup.query.filter_by(backup_id=current_backup.parent_backup_id).first()
                
            if not backup_chain or backup_chain[0].backup_type != BackupType.FULL.value:
                raise Exception("Could not find base full backup")
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
                    raise Exception(f"Database restore failed for {backup.backup_id}: {result.stderr}")

            # Restore files from the backup chain
            repository_dir = 'research_repository'
            if os.path.exists(repository_dir):
                shutil.rmtree(repository_dir)
            os.makedirs(repository_dir)

            # Restore files from each backup in the chain
            for backup in backup_chain:
                archive_path = os.path.join(backup.files_backup_location, 'repository_backup.tar.xz')
                if os.path.exists(archive_path) and os.path.getsize(archive_path) > 0:
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