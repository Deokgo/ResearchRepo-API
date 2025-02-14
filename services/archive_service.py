import csv
import json
from datetime import datetime, timedelta
import os
from models import db, Account
from services.auth_services import log_audit_trail

class AccountArchiver:
    def __init__(self):
        self.archive_dir = 'archives/accounts'
        os.makedirs(self.archive_dir, exist_ok=True)

    def archive_accounts(self, archive_type, days):
        """
        Archive accounts based on specified criteria:
        - Inactive accounts (no login for X days)
        - Deactivated accounts (deactivated for X days)
        """
        current_date = datetime.utcnow()
        
        # Build query based on archive type
        if archive_type == "INACTIVE":
            accounts_to_archive = Account.query.filter(
                Account.last_login.isnot(None),
                Account.last_login <= current_date - timedelta(days=days)
            ).all()
        elif archive_type == "DEACTIVATED":
            accounts_to_archive = Account.query.filter(
                Account.acc_status == 'DEACTIVATED',
                Account.updated_at <= current_date - timedelta(days=days)
            ).all()
        else:
            raise ValueError("Invalid archive type")

        if not accounts_to_archive:
            return {"message": "No accounts to archive", "count": 0}

        # Create archive files
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        archive_name = f'{archive_type.lower()}_accounts_{timestamp}'
        
        # Export to CSV and JSON
        csv_filename = os.path.join(self.archive_dir, f'{archive_name}.csv')
        json_filename = os.path.join(self.archive_dir, f'{archive_name}.json')
        
        self._export_to_csv(accounts_to_archive, csv_filename)
        self._export_to_json(accounts_to_archive, json_filename)

        # Log archives and delete accounts
        archived_count = 0
        for account in accounts_to_archive:
            try:
                archive_reason = (
                    f"Account {archive_type.lower()} for over {days} days"
                )
                
                # Log the archival
                log_audit_trail(
                    email="system@example.com",
                    role="SYSTEM",
                    table_name="Account",
                    record_id=account.user_id,
                    operation="ARCHIVE",
                    action_desc=f"Account archived: {archive_reason}. Exported to {archive_name}"
                )

                # Delete the account
                db.session.delete(account)
                archived_count += 1

            except Exception as e:
                print(f"Error archiving account {account.user_id}: {str(e)}")
                continue

        db.session.commit()
        return {
            "message": f"Successfully archived {archived_count} accounts",
            "count": archived_count,
            "csv_file": csv_filename,
            "json_file": json_filename
        }

    def _export_to_csv(self, accounts, filename):
        """Export accounts to CSV file"""
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = [
                'user_id', 'email', 'role_id', 'acc_status',
                'last_login', 'created_at', 'updated_at'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for account in accounts:
                writer.writerow({
                    'user_id': account.user_id,
                    'email': account.email,
                    'role_id': account.role_id,
                    'acc_status': account.acc_status,
                    'last_login': account.last_login,
                    'created_at': account.created_at,
                    'updated_at': account.updated_at
                })

    def _export_to_json(self, accounts, filename):
        """Export accounts to JSON file with complete data"""
        accounts_data = []
        for account in accounts:
            account_data = {
                'user_id': account.user_id,
                'email': account.email,
                'role_id': account.role_id,
                'acc_status': account.acc_status,
                'last_login': account.last_login.isoformat() if account.last_login else None,
                'created_at': account.created_at.isoformat(),
                'updated_at': account.updated_at.isoformat(),
                'user_profile': {
                    'first_name': account.user_profile.first_name if account.user_profile else None,
                    'last_name': account.user_profile.last_name if account.user_profile else None,
                    'college_id': account.user_profile.college_id if account.user_profile else None,
                    'program_id': account.user_profile.program_id if account.user_profile else None
                } if account.user_profile else None
            }
            accounts_data.append(account_data)

        with open(filename, 'w') as jsonfile:
            json.dump(accounts_data, jsonfile, indent=2) 