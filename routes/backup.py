from flask import Blueprint, jsonify, current_app, request, send_file
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
from flask_jwt_extended import get_jwt_identity, create_access_token
import hashlib
import time
from sqlalchemy import create_engine
from models import Account
import json
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask.cli import with_appcontext

backup = Blueprint('backup', __name__)

class BackupType(Enum):
    FULL = 'FULL'
    INCREMENTAL = 'INCR'

def generate_backup_id(backup_type):
    # Format: BK_FULL_YYYYMMDD_HHMMSS or BK_INCR_YYYYMMDD_HHMMSS
    timestamp = datetime.now().strftime(f'BK_{backup_type.value}_%Y%m%d_%H%M%S')
    return timestamp

def get_changed_files(repository_dir, last_backup_date):
    """Get list of files that have changed since last backup"""
    changed_files = []
    for root, _, files in os.walk(repository_dir):
        for file in files:
            filepath = os.path.join(root, file)
            # Check if file was modified after last backup
            if os.path.getmtime(filepath) > last_backup_date.timestamp():
                changed_files.append(filepath)
    return changed_files

def calculate_backup_hash(backup_dir):
    """Calculate SHA-256 hash of all backup files"""
    sha256_hash = hashlib.sha256()
    
    # Get root backup directory if we're in a subdirectory
    root_backup_dir = os.path.dirname(backup_dir) if os.path.basename(backup_dir) in ['database', 'files'] else backup_dir
    
    # Get all files in the backup directory and sort them for consistent ordering
    all_files = []
    for root, _, files in os.walk(root_backup_dir):
        for file in files:
            if file != 'integrity.json':  # Skip the integrity file itself
                filepath = os.path.join(root, file)
                all_files.append(filepath)
    
    # Sort files for consistent hashing
    all_files.sort()
    
    # Calculate hash of all files
    for filepath in all_files:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256_hash.update(chunk)
    
    return sha256_hash.hexdigest()

def create_backup_hash(backup_id, backup_type, backup_dir):
    """Create integrity.json with backup metadata and hash"""
    manifest = {
        'backup_id': backup_id,
        'creation_date': datetime.now().isoformat(),
        'backup_type': backup_type.value,
        'files': {},
        'backup_hash': calculate_backup_hash(backup_dir)
    }
    
    # Add individual file information
    for root, _, files in os.walk(backup_dir):
        for file in files:
            if file != 'integrity.json':  
                filepath = os.path.join(root, file)
                relpath = os.path.relpath(filepath, backup_dir)
                with open(filepath, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                manifest['files'][relpath] = file_hash
    
    # Write integrity file
    manifest_path = os.path.join(backup_dir, 'integrity.json')  # Changed from manifest.json
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    return manifest

def verify_backup_integrity(backup_dir):
    """Verify backup integrity using integrity.json"""
    print(f"Checking integrity for backup directory: {backup_dir}")
    
    # Get root backup directory if we're in a subdirectory
    root_backup_dir = os.path.dirname(backup_dir) if os.path.basename(backup_dir) in ['database', 'files'] else backup_dir
    manifest_path = os.path.join(root_backup_dir, 'integrity.json')
    print(f"Looking for integrity file at: {manifest_path}")
    
    # Check if directory exists
    if not os.path.exists(backup_dir):
        raise Exception(f"Backup directory not found: {backup_dir}")
    
    # List contents of backup directory
    print("Backup directory contents:")
    for root, dirs, files in os.walk(backup_dir):
        for file in files:
            print(f"- {os.path.join(root, file)}")
    
    if not os.path.exists(manifest_path):
        raise Exception(f"Backup integrity file not found at: {manifest_path}")
    
    print("Found integrity.json, reading contents...")
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    print("Calculating current backup hash...")
    current_hash = calculate_backup_hash(backup_dir)
    print(f"Stored hash: {manifest['backup_hash']}")
    print(f"Current hash: {current_hash}")
    
    if current_hash != manifest['backup_hash']:
        raise Exception("Backup integrity check failed: Overall hash mismatch")
    
    print("Verifying individual files...")
    # Verify individual files
    for relpath, stored_hash in manifest['files'].items():
        # Use the root backup directory for the full filepath
        filepath = os.path.join(root_backup_dir, relpath)
        if not os.path.exists(filepath):
            raise Exception(f"File missing from backup: {relpath}")
        
        with open(filepath, 'rb') as f:
            current_file_hash = hashlib.sha256(f.read()).hexdigest()
        
        if current_file_hash != stored_hash:
            raise Exception(f"File integrity check failed: {relpath}")
    
    print("Integrity verification completed successfully")
    return True

@backup.route('/create/<backup_type>', methods=['POST'])
@admin_required
def create_backup(backup_type):
    try:
        # Get the current user for audit trail
        current_user = Account.query.get(get_jwt_identity())
        if not current_user:
            return jsonify({"error": "Current user not found"}), 404

        backup_type = BackupType(backup_type.upper())
        
        # If it's an incremental backup, find the latest backup in current timeline
        parent_backup_id = None
        if backup_type == BackupType.INCREMENTAL:
            current_timeline = get_current_timeline()
            latest_backup = Backup.query.filter_by(
                timeline_id=current_timeline
            ).order_by(Backup.backup_date.desc()).first()
            
            if not latest_backup:
                return jsonify({
                    'error': 'Cannot create incremental backup: No full backup exists in the current timeline. Please create a full backup first.'
                }), 400
            
            parent_backup_id = latest_backup.backup_id

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
                pg_bin = r'C:\Program Files\PostgreSQL\16\bin'
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

                # Backup repository files for full backup
                repository_dir = 'research_repository'
                if os.path.exists(repository_dir):
                    archive_path = os.path.join(files_backup_dir, 'repository_backup.tar.xz')
                    print(f"Creating full backup of repository files at: {archive_path}")
                    with tarfile.open(archive_path, "w:xz", preset=9 | lzma.PRESET_EXTREME) as tar:
                        tar.add(repository_dir, arcname=os.path.basename(repository_dir))
                
            else:  # Incremental backup
                # Get PostgreSQL data directory from config
                pgdata = current_app.config.get('PGDATA')
                if not pgdata:
                    raise Exception("PGDATA path not configured in application settings")

                # Convert path to proper format for the current OS
                pgdata = os.path.normpath(pgdata)
                print(f"Using PGDATA path: {pgdata}")

                # Get last backup (either full or incremental)
                last_backup = Backup.query.order_by(Backup.backup_date.desc()).first()
                if not last_backup:
                    raise Exception("No previous backup found. Please create a full backup first")

                # Create WAL archive directory
                wal_dir = os.path.join(db_backup_dir, 'wal')
                os.makedirs(wal_dir, exist_ok=True)

                # Force a WAL switch to ensure all changes are in WAL files
                with db.engine.connect() as conn:
                    conn.execute(text("SELECT pg_switch_wal()"))

                # Get current WAL location after switch
                current_lsn = get_current_wal_lsn(pg_bin, host, db_user, db_name)
                print(f"Current WAL LSN: {current_lsn}")

                # Get last backup's LSN
                last_lsn = last_backup.wal_lsn or '0/0'
                print(f"Last backup LSN: {last_lsn}")

                # Query to check for changes
                check_changes_query = """
                SELECT EXISTS (
                    SELECT 1 
                    FROM pg_stat_database 
                    WHERE datname = current_database() 
                    AND (xact_commit + xact_rollback) > 0 
                    AND stats_reset > :last_backup_date
                );
                """
                
                with db.engine.connect() as conn:
                    has_changes = conn.execute(
                        text(check_changes_query), 
                        {"last_backup_date": last_backup.backup_date}
                    ).scalar()
                    
                    if not has_changes and current_lsn == last_lsn:
                        raise Exception("No changes detected since last backup.")

                # Get the minimum necessary WAL files
                pg_wal_path = os.path.join(pgdata, 'pg_wal')
                if not os.path.exists(pg_wal_path):
                    raise Exception(f"WAL directory not found: {pg_wal_path}")

                # Create a temporary directory for WAL segment extraction
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Get only the most recent WAL file
                    latest_wal = None
                    latest_timestamp = 0

                    for filename in os.listdir(pg_wal_path):
                        if filename.startswith('0000'):
                            filepath = os.path.join(pg_wal_path, filename)
                            file_timestamp = os.path.getmtime(filepath)
                            if file_timestamp > latest_timestamp:
                                latest_timestamp = file_timestamp
                                latest_wal = filename

                    if not latest_wal:
                        raise Exception("No WAL files found after detecting changes.")

                    # Copy and compress only the relevant portion of the WAL file
                    src = os.path.join(pg_wal_path, latest_wal)
                    temp_wal = os.path.join(temp_dir, latest_wal)
                    
                    # Copy the WAL file to temp directory
                    shutil.copy2(src, temp_wal)
                    
                    # Create a highly compressed archive of the WAL file
                    wal_archive = os.path.join(db_backup_dir, 'wal.xz')
                    with open(temp_wal, 'rb') as f_in:
                        with lzma.open(wal_archive, 'wb', preset=9 | lzma.PRESET_EXTREME) as f_out:
                            shutil.copyfileobj(f_in, f_out)

                # Backup changed repository files for incremental backup
                repository_dir = 'research_repository'
                if os.path.exists(repository_dir):
                    last_backup = Backup.query.filter(
                        Backup.backup_date < datetime.now()
                    ).order_by(Backup.backup_date.desc()).first()
                    
                    if last_backup:
                        changed_files = get_changed_files(repository_dir, last_backup.backup_date)
                        if changed_files:
                            archive_path = os.path.join(files_backup_dir, 'repository_backup.tar.xz')
                            print(f"Creating incremental backup of repository files at: {archive_path}")
                            with tarfile.open(archive_path, "w:xz", preset=9 | lzma.PRESET_EXTREME) as tar:
                                for filepath in changed_files:
                                    arcname = os.path.relpath(filepath, start=os.path.dirname(repository_dir))
                                    tar.add(filepath, arcname=arcname)

                # Create backup.info file with metadata
                backup_info_path = os.path.join(db_backup_dir, 'backup.info')
                with open(backup_info_path, 'w') as f:
                    f.write(f"backup_id={backup_id}\n")
                    f.write(f"backup_type={backup_type.value}\n")
                    f.write(f"parent_backup_id={parent_backup_id}\n")
                    f.write(f"start_wal_location={last_lsn}\n")
                    f.write(f"end_wal_location={current_lsn}\n")
                    f.write(f"backup_date={datetime.now().isoformat()}\n")
                    f.write(f"wal_file={latest_wal}\n")

            # After creating the backup files but before creating the database record,
            # generate and store the integrity information
            try:
                manifest = create_backup_hash(backup_id, backup_type, backup_dir)
                print(f"Created integrity manifest for backup {backup_id}")
            except Exception as e:
                raise Exception(f"Failed to create integrity manifest: {str(e)}")

            # Calculate total size (include integrity.json in the total)
            total_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(backup_dir)
                for filename in filenames
            )

            # Create backup record
            backup = Backup(
                backup_id=backup_id,
                backup_type=backup_type.value,
                backup_date=datetime.now(),
                timeline_id=get_current_timeline(),
                database_backup_location=db_backup_dir,
                files_backup_location=files_backup_dir,
                total_size=total_size,
                parent_backup_id=parent_backup_id
            )
            db.session.add(backup)
            db.session.commit()

            log_audit_trail(
                email=current_user.email,
                role=current_user.role.role_name,
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
        # Before stopping PostgreSQL, eagerly load the user and role data
        current_user = Account.query.options(db.joinedload(Account.role)).get(get_jwt_identity())
        if not current_user:
            return jsonify({"error": "Current user not found"}), 404

        # Store the needed information
        user_info = {
            'email': current_user.email,
            'role_name': current_user.role.role_name  # Get this before closing connection
        }

        # Get PGDATA path from config at the start
        pgdata = current_app.config.get('PGDATA')
        if not pgdata:
            raise Exception("PGDATA path not configured in application settings")
        
        # Convert path to proper format for the current OS
        pgdata = os.path.normpath(pgdata)
        print(f"Using PGDATA path: {pgdata}")

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

        # Verify backup integrity before proceeding with restore
        try:
            verify_backup_integrity(backup_info['database_backup_location'])
            if os.path.exists(backup_info['files_backup_location']):
                verify_backup_integrity(backup_info['files_backup_location'])
            print("Backup integrity verified successfully")
        except Exception as e:
            raise Exception(f"Backup integrity check failed: {str(e)}")

        if target_backup.backup_type == BackupType.FULL.value:
            # --- SERVICE CONTROL: Stop PostgreSQL ---
            if platform.system() == 'Windows':
                # Find PostgreSQL service name
                list_command = 'sc query state= all | findstr /I "postgresql"'
                result = subprocess.run(list_command, shell=True, capture_output=True, text=True)
                service_output = result.stdout.lower()
                if 'postgresql-x64-16' in service_output:
                    service_name = 'postgresql-x64-16'
                elif 'postgresql-16' in service_output:
                    service_name = 'postgresql-16'
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
                            pg_bin = r'C:\Program Files\PostgreSQL\16\bin'
                        print(f"Using PostgreSQL binaries from: {pg_bin}")

                        # First, stop PostgreSQL and clean data directory
                        if os.path.exists(pgdata):
                            shutil.rmtree(pgdata)
                        os.makedirs(pgdata)

                        # Verify backup files
                        verify_backup_manifest(backup_info['database_backup_location'])
                        
                        # Extract base backup
                        base_backup_file = os.path.join(backup_info['database_backup_location'], 'base.tar.gz')
                        if not os.path.exists(base_backup_file):
                            raise Exception(f"Backup file not found: {base_backup_file}")

                        print("Extracting base backup...")
                        with tarfile.open(base_backup_file, "r:gz") as tar:
                            tar.extractall(path=pgdata)

                        # Extract WAL files
                        wal_backup_file = os.path.join(backup_info['database_backup_location'], 'pg_wal.tar.gz')
                        if os.path.exists(wal_backup_file):
                            print("Extracting WAL files...")
                            pg_wal_dir = os.path.join(pgdata, 'pg_wal')
                            if not os.path.exists(pg_wal_dir):
                                os.makedirs(pg_wal_dir)
                            with tarfile.open(wal_backup_file, "r:gz") as tar:
                                tar.extractall(path=pg_wal_dir)

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
                        start_command = f'net start postgresql-x64-16'
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
                                                email=user_info['email'],
                                                role=user_info['role_name'],
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
                                # Restore repository files
                                repository_dir = 'research_repository'
                                files_backup = os.path.join(target_backup.files_backup_location, 'repository_backup.tar.xz')
                                
                                print(f"Checking for repository backup at: {files_backup}")
                                if os.path.exists(files_backup):
                                    print("Found repository backup file, starting restore...")
                                    
                                    # Backup current repository if it exists
                                    if os.path.exists(repository_dir):
                                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                        repo_backup_dir = f"{repository_dir}_backup_{timestamp}"
                                        print(f"Creating backup of current repository at: {repo_backup_dir}")
                                        shutil.copytree(repository_dir, repo_backup_dir)
                                        shutil.rmtree(repository_dir)
                                    
                                    # Create repository directory if it doesn't exist
                                    os.makedirs(repository_dir, exist_ok=True)
                                    
                                    # Extract repository files
                                    print("Extracting repository files...")
                                    with tarfile.open(files_backup, "r:xz") as tar:
                                        tar.extractall(path=os.path.dirname(repository_dir))
                                    print("Repository files restored successfully")

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
                            subprocess.run('net start postgresql-x64-16', shell=True, check=True)
                            print("Restored original data directory and restarted PostgreSQL")
                        except Exception as start_error:
                            print(f"Failed to restart PostgreSQL with original data: {start_error}")
                    
                    raise Exception(f"Restore failed: {str(e)}")

                finally:
                    # Clean up repository backup
                    if 'repo_backup_dir' in locals() and os.path.exists(repo_backup_dir):
                        try:
                            shutil.rmtree(repo_backup_dir)
                            print("Cleaned up temporary repository backup")
                        except Exception as e:
                            print(f"Warning: Could not remove temporary repository backup: {e}")

        else:
            print(f"Starting incremental restore process for backup: {backup_id}")
            
            # Get all backups in the chain by following parent_backup_id
            backups_to_restore = []
            current_backup = target_backup
            while current_backup:
                backups_to_restore.insert(0, current_backup)  # Add to start of list
                if current_backup.parent_backup_id:
                    current_backup = Backup.query.filter_by(
                        backup_id=current_backup.parent_backup_id
                    ).first()
                else:
                    break

            # Verify we have a valid chain starting with a full backup
            if not backups_to_restore or backups_to_restore[0].backup_type != BackupType.FULL.value:
                raise Exception("No base full backup found in the backup chain")

            print(f"Found base full backup: {backups_to_restore[0].backup_id}")
            
            try:
                # First restore the full backup using the existing working method
                print("Restoring base full backup...")
                base_backup_file = os.path.join(backups_to_restore[0].database_backup_location, 'base.tar.gz')
                pg_wal_backup = os.path.join(backups_to_restore[0].database_backup_location, 'pg_wal.tar.gz')
                
                if not os.path.exists(base_backup_file) or not os.path.exists(pg_wal_backup):
                    raise Exception(f"Required backup files not found in {backups_to_restore[0].database_backup_location}")

                # Stop PostgreSQL service
                print("Stopping PostgreSQL service...")
                stop_command = 'net stop postgresql-x64-16'
                subprocess.run(stop_command, shell=True, check=True)
                time.sleep(10)

                # Backup current data directory
                if os.path.exists(pgdata):
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    original_data_backup = f"{pgdata}_backup_{timestamp}"
                    print(f"Backing up current data directory to: {original_data_backup}")
                    shutil.copytree(pgdata, original_data_backup)
                    shutil.rmtree(pgdata)
                os.makedirs(pgdata)

                # Extract base backup
                print("Extracting base backup...")
                with tarfile.open(base_backup_file, "r:gz") as tar:
                    tar.extractall(path=pgdata)

                # Extract original WAL files from full backup
                print("Extracting WAL files from full backup...")
                pg_wal_dir = os.path.join(pgdata, 'pg_wal')
                os.makedirs(pg_wal_dir, exist_ok=True)
                with tarfile.open(pg_wal_backup, "r:gz") as tar:
                    tar.extractall(path=pg_wal_dir)

                # Process incremental WAL files
                print("Processing incremental WAL files...")
                for backup in backups_to_restore:
                    if backup.backup_type == BackupType.INCREMENTAL.value:
                        print(f"Processing WAL from: {backup.backup_id}")
                        wal_archive = os.path.join(backup.database_backup_location, 'wal.xz')
                        if os.path.exists(wal_archive):
                            # Read backup info to get WAL filename
                            backup_info_path = os.path.join(backup.database_backup_location, 'backup.info')
                            wal_filename = None
                            with open(backup_info_path, 'r') as f:
                                for line in f:
                                    if line.startswith('wal_file='):
                                        wal_filename = line.strip().split('=')[1]
                                        break
                            
                            if wal_filename:
                                # Extract WAL file with original filename
                                with lzma.open(wal_archive, 'rb') as f_in:
                                    wal_path = os.path.join(pg_wal_dir, wal_filename)
                                    with open(wal_path, 'wb') as f_out:
                                        shutil.copyfileobj(f_in, f_out)
                                print(f"Extracted WAL file: {wal_filename}")

                # Create recovery.signal file
                recovery_signal = os.path.join(pgdata, 'recovery.signal')
                open(recovery_signal, 'w').close()
                print("Created recovery.signal file")

                # Update postgresql.conf with recovery settings
                postgresql_conf = os.path.join(pgdata, 'postgresql.conf')
                with open(postgresql_conf, 'w') as f:
                    f.write("listen_addresses = '*'\n")
                    f.write("port = 5432\n")
                    f.write("max_connections = 100\n")
                    f.write("shared_buffers = 128MB\n")
                    f.write("dynamic_shared_memory_type = windows\n")
                    f.write("max_wal_size = 1GB\n")
                    f.write("min_wal_size = 80MB\n")
                    f.write("wal_level = replica\n")
                    f.write("restore_command = 'copy \"%p\" \"%f\"'\n")
                    f.write("recovery_target_timeline = 'latest'\n")

                # Create postgresql.auto.conf with additional settings
                auto_conf = os.path.join(pgdata, 'postgresql.auto.conf')
                with open(auto_conf, 'w') as f:
                    f.write("# Recovery configuration\n")
                    f.write("hot_standby = on\n")
                    f.write("wal_log_hints = on\n")

                # Remove backup_label if it exists
                backup_label = os.path.join(pgdata, 'backup_label')
                if os.path.exists(backup_label):
                    os.remove(backup_label)
                    print("Removed backup_label")

                # Set proper permissions
                for root, dirs, files in os.walk(pgdata):
                    for d in dirs:
                        os.chmod(os.path.join(root, d), 0o700)
                    for f in files:
                        os.chmod(os.path.join(root, f), 0o600)

                print("Starting PostgreSQL service...")
                start_command = 'net start postgresql-x64-16'
                subprocess.run(start_command, shell=True, check=True)
                time.sleep(15)

                # Test connection with retries
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        # Create a new connection to test
                        test_engine = create_engine(
                            current_app.config['SQLALCHEMY_DATABASE_URI'],
                            pool_pre_ping=True,
                            pool_timeout=30
                        )
                        with test_engine.connect() as conn:
                            conn.execute(text("SELECT 1"))
                        test_engine.dispose()
                        print("Database connection successful after restore")
                        
                        # Wait before attempting to log
                        time.sleep(5)
                        
                        # Log audit trail with retries
                        audit_max_retries = 3
                        for audit_attempt in range(audit_max_retries):
                            try:
                                # Create fresh database session
                                db.session.remove()
                                db.session.close()
                                db.engine.dispose()
                                
                                log_audit_trail(
                                    email=user_info['email'],
                                    role=user_info['role_name'],
                                    operation="RESTORE_BACKUP",
                                    action_desc=f"Restored backup with ID: {backup_id}",
                                    table_name="backup",
                                    record_id=backup_id
                                )
                                restore_successful = True
                                break
                            except Exception as audit_error:
                                print(f"Audit logging attempt {audit_attempt + 1} failed: {str(audit_error)}")
                                if audit_attempt < audit_max_retries - 1:
                                    time.sleep(5)
                        break
                    except Exception as e:
                        print(f"Connection attempt {attempt + 1} failed: {str(e)}")
                        if attempt < max_retries - 1:
                            time.sleep(10)
                        else:
                            raise

                if restore_successful:
                    # Restore incremental repository files
                    repository_dir = 'research_repository'
                    files_backup = os.path.join(target_backup.files_backup_location, 'repository_backup.tar.xz')
                    
                    if os.path.exists(files_backup):
                        print(f"Found incremental repository backup at: {files_backup}")
                        
                        # Backup current repository
                        if os.path.exists(repository_dir):
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            repo_backup_dir = f"{repository_dir}_backup_{timestamp}"
                            print(f"Creating backup of current repository at: {repo_backup_dir}")
                            shutil.copytree(repository_dir, repo_backup_dir)
                        
                        try:
                            # Extract changed files
                            print("Extracting changed repository files...")
                            with tarfile.open(files_backup, "r:xz") as tar:
                                for member in tar.getmembers():
                                    target_path = os.path.join(repository_dir, member.name)
                                    # Create parent directories if they don't exist
                                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                                    # Extract file
                                    with tar.extractfile(member) as source, open(target_path, 'wb') as target:
                                        shutil.copyfileobj(source, target)
                            print("Repository files restored successfully")
                        
                        except Exception as e:
                            print(f"Error restoring repository files: {str(e)}")
                            # Restore original repository if backup exists
                            if os.path.exists(repo_backup_dir):
                                print("Restore failed. Restoring original repository...")
                                if os.path.exists(repository_dir):
                                    shutil.rmtree(repository_dir)
                                shutil.copytree(repo_backup_dir, repository_dir)
                            raise
                        
                        finally:
                            # Clean up repository backup
                            if 'repo_backup_dir' in locals() and os.path.exists(repo_backup_dir):
                                try:
                                    shutil.rmtree(repo_backup_dir)
                                    print("Cleaned up temporary repository backup")
                                except Exception as e:
                                    print(f"Warning: Could not remove temporary repository backup: {e}")

                    return jsonify({
                        'message': 'Backup restored successfully',
                        'backup_id': backup_id
                    }), 200
                else:
                    return jsonify({
                        'error': 'Restore completed but verification failed'
                    }), 500

            except Exception as e:
                print(f"Error during incremental restore: {str(e)}")
                if 'original_data_backup' in locals() and original_data_backup and os.path.exists(original_data_backup):
                    try:
                        if os.path.exists(pgdata):
                            shutil.rmtree(pgdata)
                        shutil.copytree(original_data_backup, pgdata)
                        subprocess.run('net start postgresql-x64-16', shell=True, check=True)
                        print("Restored original data directory after failed restore")
                    except Exception as restore_error:
                        print(f"Failed to restore original data: {restore_error}")
                return jsonify({'error': str(e)}), 500
            finally:
                # Clean up repository backup
                if 'repo_backup_dir' in locals() and os.path.exists(repo_backup_dir):
                    try:
                        shutil.rmtree(repo_backup_dir)
                        print("Cleaned up temporary repository backup")
                    except Exception as e:
                        print(f"Warning: Could not remove temporary repository backup: {e}")

    except Exception as e:
        print(f"Error during restore: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500
    
@backup.route('/restore-from-file', methods=['POST'])
@admin_required
def restore_from_file():
    original_data_backup = None
    try:
        if 'backup_file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['backup_file']
        if not file.filename.endswith('.tar.gz'):
            return jsonify({'error': 'Invalid file format. Must be a .tar.gz file'}), 400

        # Create temporary directory to extract the backup
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_path = os.path.join(temp_dir, 'backup.tar.gz')
            file.save(backup_path)

            # Create a subdirectory for proper extraction
            extract_dir = os.path.join(temp_dir, 'extract')
            os.makedirs(extract_dir)

            # Extract the backup
            with tarfile.open(backup_path, 'r:gz') as tar:
                # First, extract and read the integrity.json
                for member in tar.getmembers():
                    if member.name == 'integrity.json':
                        tar.extract(member, extract_dir)
                        break
                
                integrity_file = os.path.join(extract_dir, 'integrity.json')
                if not os.path.exists(integrity_file):
                    raise Exception("Invalid backup file: Missing integrity.json file")
                
                with open(integrity_file, 'r') as f:
                    manifest = json.load(f)
                stored_hash = manifest['backup_hash']
                
                # Now extract everything else
                tar.extractall(path=extract_dir)
            
            # Print directory structure for debugging
            print("\nExtracted directory structure:")
            for root, dirs, files in os.walk(extract_dir):
                level = root.replace(extract_dir, '').count(os.sep)
                indent = ' ' * 4 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 4 * (level + 1)
                for f in files:
                    print(f"{subindent}{f}")

            # Verify backup structure
            database_dir = os.path.join(extract_dir, 'database')
            if not os.path.exists(database_dir):
                raise Exception("Invalid backup file: Missing database directory")
            
            # Calculate hash of extracted files
            current_hash = calculate_backup_hash(extract_dir)
            print(f"\nHash comparison:")
            print(f"Stored hash:   {stored_hash}")
            print(f"Current hash:  {current_hash}")
            
            if current_hash != stored_hash:
                raise Exception("Backup integrity check failed: Hash mismatch")

            print("Backup integrity verified successfully")

            # Stop PostgreSQL service
            print("Stopping PostgreSQL service...")
            subprocess.run('net stop postgresql-x64-16', shell=True, check=True)
            time.sleep(10)

            # Backup current PGDATA
            pgdata = current_app.config.get('PGDATA')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            original_data_backup = f"{pgdata}_backup_{timestamp}"
            if os.path.exists(pgdata):
                shutil.copytree(pgdata, original_data_backup)
                shutil.rmtree(pgdata)
            os.makedirs(pgdata)

            try:
                # Extract base backup
                base_backup = os.path.join(database_dir, 'base.tar.gz')
                with tarfile.open(base_backup, 'r:gz') as tar:
                    tar.extractall(path=pgdata)

                # Extract WAL files if they exist
                pg_wal_backup = os.path.join(database_dir, 'pg_wal.tar.gz')
                if os.path.exists(pg_wal_backup):
                    pg_wal_dir = os.path.join(pgdata, 'pg_wal')
                    os.makedirs(pg_wal_dir, exist_ok=True)
                    with tarfile.open(pg_wal_backup, 'r:gz') as tar:
                        tar.extractall(path=pg_wal_dir)

                # Create recovery.signal file
                recovery_signal = os.path.join(pgdata, 'recovery.signal')
                open(recovery_signal, 'w').close()

                # Update postgresql.conf
                postgresql_conf = os.path.join(pgdata, 'postgresql.conf')
                with open(postgresql_conf, 'w') as f:
                    f.write("listen_addresses = '*'\n")
                    f.write("port = 5432\n")
                    f.write("max_connections = 100\n")
                    f.write("shared_buffers = 128MB\n")
                    f.write("dynamic_shared_memory_type = windows\n")
                    f.write("max_wal_size = 1GB\n")
                    f.write("min_wal_size = 80MB\n")
                    f.write("wal_level = replica\n")
                    f.write("restore_command = 'copy \"%p\" \"%f\"'\n")
                    f.write("recovery_target_timeline = 'latest'\n")

                # Set proper permissions
                for root, dirs, files in os.walk(pgdata):
                    for d in dirs:
                        os.chmod(os.path.join(root, d), 0o700)
                    for f in files:
                        os.chmod(os.path.join(root, f), 0o600)

                # Start PostgreSQL service
                print("Starting PostgreSQL service...")
                subprocess.run('net start postgresql-x64-16', shell=True, check=True)
                time.sleep(15)

                # Test connection with retries
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        # Create a new connection to test
                        test_engine = create_engine(
                            current_app.config['SQLALCHEMY_DATABASE_URI'],
                            pool_pre_ping=True,
                            pool_timeout=30
                        )
                        with test_engine.connect() as conn:
                            conn.execute(text("SELECT 1"))
                        test_engine.dispose()
                        print("Database connection successful")
                        
                        # Close existing connections
                        db.session.remove()
                        db.session.close()
                        db.engine.dispose()
                        
                        # Wait before attempting to log
                        time.sleep(5)
                        
                        # Log audit trail
                        break
                    except Exception as e:
                        print(f"Connection attempt {attempt + 1} failed: {str(e)}")
                        if attempt < max_retries - 1:
                            time.sleep(10)
                        else:
                            raise Exception("Failed to establish database connection")

                # Restore repository files
                repository_dir = 'research_repository'
                files_dir = os.path.join(temp_dir, 'files')
                if os.path.exists(files_dir):
                    if os.path.exists(repository_dir):
                        shutil.rmtree(repository_dir)
                    shutil.copytree(files_dir, repository_dir)

                return jsonify({'message': 'Backup restored successfully'}), 200
            except Exception as e:
                # Restore original data on failure
                if os.path.exists(original_data_backup):
                    if os.path.exists(pgdata):
                        shutil.rmtree(pgdata)
                    shutil.copytree(original_data_backup, pgdata)
                    subprocess.run('net start postgresql-x64-16', shell=True, check=True)
                raise

    except Exception as e:
        print(f"Error restoring from file: {str(e)}")
        return jsonify({'error': str(e)}), 500

    finally:
        # Clean up backup directory
        if original_data_backup and os.path.exists(original_data_backup):
            try:
                shutil.rmtree(original_data_backup)
            except Exception as e:
                print(f"Warning: Could not remove temporary backup: {e}")

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
                'timeline_id': b.timeline_id,
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

def verify_backup_manifest(backup_location):
    manifest_file = os.path.join(backup_location, 'backup_manifest')
    if not os.path.exists(manifest_file):
        raise Exception("backup_manifest file not found")
    # TODO: Add manifest validation logic
    return True

def get_wal_files_between(start_lsn, end_lsn, pg_bin, pgdata):
    """Get list of WAL files between two LSN positions"""
    pg_waldump_exe = os.path.join(
        pg_bin, 
        'pg_waldump.exe' if platform.system() == 'Windows' else 'pg_waldump'
    )
    
    command = f'"{pg_waldump_exe}" --path="{os.path.join(pgdata, "pg_wal")}" ' \
              f'--start={start_lsn} ' \
              f'--end={end_lsn} ' \
              f'--list-only'
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Failed to list WAL files: {result.stderr}")
    
    return [line.split()[0] for line in result.stdout.splitlines() if line.strip()]

def get_current_timeline():
    """Get current timeline ID from PostgreSQL"""
    query = "SELECT timeline_id FROM pg_control_checkpoint();"
    with db.engine.connect() as conn:
        result = conn.execute(text(query)).scalar()
    return result

@backup.route('/current-timeline', methods=['GET'])
@admin_required
def get_current_timeline_route():
    try:
        # Get current timeline ID from PostgreSQL
        query = "SELECT timeline_id FROM pg_control_checkpoint();"
        with db.engine.connect() as conn:
            result = conn.execute(text(query)).scalar()
        
        return jsonify({
            'timeline_id': result
        }), 200
    except Exception as e:
        print(f"Error getting current timeline: {str(e)}")
        return jsonify({'error': str(e)}), 500

@backup.route('/download/<backup_id>', methods=['GET'])
@admin_required
def download_backup(backup_id):
    try:
        backup = Backup.query.filter_by(backup_id=backup_id).first()
        if not backup:
            return jsonify({'error': 'Backup not found'}), 404

        # Get root backup directory
        root_backup_dir = os.path.dirname(backup.database_backup_location)

        # Create a temporary file to store the backup
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as temp_file:
            with tarfile.open(temp_file.name, 'w:gz') as tar:
                # Add database backup
                tar.add(backup.database_backup_location, 
                       arcname=os.path.basename(backup.database_backup_location))
                # Add files backup if it exists
                if os.path.exists(backup.files_backup_location):
                    tar.add(backup.files_backup_location, 
                           arcname=os.path.basename(backup.files_backup_location))
                # Add integrity.json file
                integrity_file = os.path.join(root_backup_dir, 'integrity.json')
                if os.path.exists(integrity_file):
                    tar.add(integrity_file, arcname='integrity.json')

        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=f'{backup_id}.tar.gz',
            mimetype='application/gzip'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Initialize scheduler
scheduler = BackgroundScheduler()

def schedule_backups():
    """Setup automated backup schedules"""
    # Remove any existing jobs first
    scheduler.remove_all_jobs()
    
    # Schedule full backup every Sunday at midnight
    scheduler.add_job(
        func=create_automated_full_backup,
        trigger=CronTrigger(
            day_of_week='sun',
            hour=0,
            minute=0
        ),
        id='full_backup_job',
        name='Weekly Full Backup',
        replace_existing=True,
        max_instances=1
    )

    # Schedule incremental backup every day at midnight except Sunday
    scheduler.add_job(
        func=create_automated_incremental_backup,
        trigger=CronTrigger(
            # day_of_week='mon-sat',
            hour=14,
            minute=27
        ),
        id='incremental_backup_job',
        name='Daily Incremental Backup',
        replace_existing=True,
        max_instances=1
    )

    # Start the scheduler if it's not already running
    if not scheduler.running:
        scheduler.start()
        print("Backup scheduler started")

def create_automated_full_backup():
    """Create automated full backup"""
    try:
        print(f"Starting automated full backup at {datetime.now()}")
        # Get the application instance
        from server import app  # Import here to avoid circular import
        
        # Move everything inside the app context
        with app.app_context():
            # Get admin user inside app context
            admin_user = Account.query.filter_by(role_id="01").first()
            if not admin_user:
                print("No admin user found in database")
                return
                
            # Create an admin token with the actual admin user's ID
            admin_token = create_access_token(
                identity=admin_user.user_id,  # Use actual admin user ID
                additional_claims={
                    "is_admin": True,
                    "role": "admin",
                    "role_name": "admin",
                    "role_id": "01"
                }
            )
            
            with app.test_request_context() as ctx:
                ctx.request.headers = {
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                }
                
                # Pass the backup type as a string value
                backup_type = BackupType.FULL.value
                response = create_backup(backup_type)
                
                if hasattr(response, 'get_json'):
                    response_data = response.get_json()
                    status_code = response.status_code
                elif isinstance(response, tuple):
                    response_data, status_code = response
                else:
                    print(f"Unexpected response type: {type(response)}")
                    return
                
                if status_code == 200:
                    backup_id = response_data.get('backup_id')
                    print(f"Automated full backup completed successfully. Backup ID: {backup_id}")
                else:
                    print(f"Backup failed with status code {status_code}: {response_data}")
    except Exception as e:
        print(f"Automated full backup failed: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")

def create_automated_incremental_backup():
    """Create automated incremental backup"""
    try:
        print(f"Starting automated incremental backup at {datetime.now()}")
        # Get the application instance
        from server import app  # Import here to avoid circular import
        
        # Move everything inside the app context
        with app.app_context():
            # Get admin user inside app context
            admin_user = Account.query.filter_by(role_id="01").first()
            if not admin_user:
                print("No admin user found in database")
                return
                
            # Create an admin token with the actual admin user's ID
            admin_token = create_access_token(
                identity=admin_user.user_id,  # Use actual admin user ID
                additional_claims={
                    "is_admin": True,
                    "role": "admin",
                    "role_name": "admin",
                    "role_id": "01"
                }
            )
            
            with app.test_request_context() as ctx:
                ctx.request.headers = {
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                }
                
                # Pass the backup type as a string value
                backup_type = BackupType.INCREMENTAL.value
                response = create_backup(backup_type)
                
                if hasattr(response, 'get_json'):
                    response_data = response.get_json()
                    status_code = response.status_code
                elif isinstance(response, tuple):
                    response_data, status_code = response
                else:
                    print(f"Unexpected response type: {type(response)}")
                    return
                
                if status_code == 200:
                    backup_id = response_data.get('backup_id')
                    print(f"Automated incremental backup completed successfully. Backup ID: {backup_id}")
                else:
                    print(f"Backup failed with status code {status_code}: {response_data}")
    except Exception as e:
        print(f"Automated incremental backup failed: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")

# Initialize the scheduler when the module loads
schedule_backups()

