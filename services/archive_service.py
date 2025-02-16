import json
from datetime import datetime, timedelta
import os
import subprocess
from models import db, Account, Visitor
from services.auth_services import log_audit_trail
from flask import current_app
from sqlalchemy import text
from flask_jwt_extended import get_jwt_identity

class AccountArchiver:
    def __init__(self):
        self.archive_dir = 'archives/accounts'
        os.makedirs(self.archive_dir, exist_ok=True)

    def archive_accounts(self, archive_type, days):
        """
        Archive accounts based on specified criteria:
        - INACTIVE: no login for X days or never logged in since creation
        - DEACTIVATED: deactivated for X days
        - ALL: both inactive and deactivated accounts
        """
        try:
            # Get current user info for audit trail
            current_user = Account.query.options(db.joinedload(Account.role)).get(get_jwt_identity())
            if not current_user:
                return {"error": "Current user not found"}, 404

            # Store user info
            user_info = {
                'email': current_user.email,
                'role_name': current_user.role.role_name
            }

            current_date = datetime.utcnow()
            accounts_to_archive = []

            if archive_type in ["INACTIVE", "ALL"]:
                # Get accounts that haven't logged in for X days
                inactive_with_login = Account.query.filter(
                    Account.last_login.isnot(None),
                    Account.last_login <= current_date - timedelta(days=days)
                ).all()
                
                # Get accounts that have never logged in and were created X days ago
                never_logged_in = Account.query.filter(
                    Account.last_login.is_(None),
                    Account.created_at <= current_date - timedelta(days=days)
                ).all()
                
                accounts_to_archive.extend(inactive_with_login)
                accounts_to_archive.extend(never_logged_in)

            if archive_type in ["DEACTIVATED", "ALL"]:
                deactivated_accounts = Account.query.filter(
                    Account.acc_status == 'DEACTIVATED',
                    Account.updated_at <= current_date - timedelta(days=days)
                ).all()
                # Avoid duplicates if an account is both inactive and deactivated
                deactivated_ids = {acc.user_id for acc in accounts_to_archive}
                accounts_to_archive.extend([acc for acc in deactivated_accounts 
                                         if acc.user_id not in deactivated_ids])

            if not accounts_to_archive:
                return {"message": "No accounts to archive", "count": 0}

            # Create archive files
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            archive_name = f'{archive_type.lower()}_accounts_{timestamp}'
            
            # Export to SQL dump
            sql_filename = os.path.join(self.archive_dir, f'{archive_name}.sql')
            backup_success = self._export_to_sql_dump(accounts_to_archive, sql_filename)

            if not backup_success:
                return {"error": "Failed to create SQL backup"}, 500

            # Delete accounts and count
            archived_count = 0
            for account in accounts_to_archive:
                try:
                    # Delete visitor record first if it exists
                    visitor = db.session.query(Visitor).filter_by(visitor_id=account.user_id).first()
                    if visitor:
                        db.session.delete(visitor)
                    
                    # Now delete the account
                    db.session.delete(account)
                    archived_count += 1
                except Exception as e:
                    print(f"Error archiving account {account.user_id}: {str(e)}")
                    continue

            if archived_count > 0:
                log_audit_trail(
                    email=user_info['email'],
                    role=user_info['role_name'],
                    table_name="Account",
                    record_id=None,  
                    operation="ARCHIVE",
                    action_desc=f"Archived {archived_count} accounts ({archive_type} archive, {days} days threshold). Exported to {archive_name}"
                )

            db.session.commit()
            return {
                "message": f"Successfully archived {archived_count} accounts",
                "count": archived_count,
                "sql_file": sql_filename
            }

        except Exception as e:
            print(f"Error during archival: {str(e)}")
            return {"error": str(e)}, 500

    def _export_to_sql_dump(self, accounts, filename):
        """Export accounts to PostgreSQL dump file"""
        try:
            # Get database configuration from Flask app
            db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
            pg_bin = current_app.config['PG_BIN']
            
            if not pg_bin:
                raise Exception("PostgreSQL binary path not configured")
            
            db_info = db_uri.replace('postgresql://', '').split('/')
            db_credentials = db_info[0].split('@')
            user_pass = db_credentials[0].split(':')
            host_port = db_credentials[1].split(':')

            username = user_pass[0]
            password = user_pass[1]
            host = host_port[0]
            port = host_port[1] if len(host_port) > 1 else '5432'
            database = db_info[1]

            # Create list of user IDs to archive
            user_ids = [f"'{account.user_id}'" for account in accounts]
            user_ids_str = ','.join(user_ids)

            # Create temporary tables using SQLAlchemy's text()
            create_tables_sql = text(f"""
                CREATE TABLE public.accounts_to_archive AS 
                SELECT * FROM account WHERE user_id IN ({user_ids_str});
                
                CREATE TABLE public.profiles_to_archive AS 
                SELECT * FROM user_profile WHERE researcher_id IN ({user_ids_str});

                CREATE TABLE public.visitors_to_archive AS 
                SELECT * FROM visitor WHERE visitor_id IN ({user_ids_str});
            """)
            
            db.session.execute(create_tables_sql)
            db.session.commit()

            # Set PGPASSWORD environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = password

            # Use full path to pg_dump
            pg_dump_path = os.path.join(pg_bin, 'pg_dump')
            
            # Create archives directory if it doesn't exist
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            # Construct pg_dump command for the tables
            cmd = [
                pg_dump_path,
                '-h', host,
                '-p', port,
                '-U', username,
                '-d', database,
                '-t', 'public.accounts_to_archive',
                '-t', 'public.profiles_to_archive',
                '-t', 'public.visitors_to_archive',
                '--data-only',
                '-a',
                '--column-inserts',
                '--inserts',
                '-w',
                '-f', filename
            ]

            # Execute pg_dump
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            # Clean up tables using text()
            cleanup_sql = text("""
                DROP TABLE IF EXISTS public.accounts_to_archive;
                DROP TABLE IF EXISTS public.profiles_to_archive;
                DROP TABLE IF EXISTS public.visitors_to_archive;
            """)
            db.session.execute(cleanup_sql)
            db.session.commit()

            if result.returncode != 0:
                print(f"Error during pg_dump: {result.stderr}")
                return False

            # Read the original content
            with open(filename, 'r') as f:
                content = f.read()
            
            # Replace table names with actual table names
            content = content.replace('INSERT INTO public.accounts_to_archive', 'INSERT INTO public.account')
            content = content.replace('INSERT INTO public.profiles_to_archive', 'INSERT INTO public.user_profile')
            content = content.replace('INSERT INTO public.visitors_to_archive', 'INSERT INTO public.visitor')
            
            # Add transaction markers and write modified content
            with open(filename, 'w') as f:
                f.write("BEGIN;\n\n")
                f.write("-- Archived accounts data dump\n")
                f.write("-- Generated on: " + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC') + "\n\n")
                f.write(content)
                f.write("\nCOMMIT;\n")

            return True

        except Exception as e:
            print(f"Error creating SQL dump: {str(e)}")
            # Clean up tables in case of error
            cleanup_sql = text("""
                DROP TABLE IF EXISTS public.accounts_to_archive;
                DROP TABLE IF EXISTS public.profiles_to_archive;
                DROP TABLE IF EXISTS public.visitors_to_archive;
            """)
            db.session.execute(cleanup_sql)
            db.session.commit()
            return False 