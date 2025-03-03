from flask import Blueprint, jsonify
import pandas as pd
from models import (
    db, Account, UserProfile, ResearchOutput, ResearchOutputAuthor, 
    SDG, Keywords, Panel, College, Program, ResearchArea, ResearchOutputArea
)
from werkzeug.security import generate_password_hash
import random
from datetime import datetime, timedelta
import pytz
import os
from services import auth_services

populate = Blueprint('populate', __name__)

@populate.route('/populate_from_csv', methods=['POST'])
def populate_from_csv():
    try:
        # Get the directory where this file is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(current_dir, 'webofscience.csv')
        
        # Read the CSV file from the routes directory
        df = pd.read_csv(csv_path)
        
        # Limit to 6000 rows
        df = df.head(6000)
        
        # Get existing colleges and programs for random assignment
        colleges = College.query.all()
        programs = Program.query.all()
        college_ids = [college.college_id for college in colleges]
        program_ids = [program.program_id for program in programs]
        
        # List of possible SDGs for random assignment
        sdg_list = [f'SDG {i}' for i in range(1, 18)]  # SDG 1 through SDG 17
        
        # Batch processing settings
        batch_size = 100
        total_processed = 0
        
        # Start with a base date and initialize counters
        base_date = datetime(2024, 1, 25)  # Start from January 25, 2024
        current_date_str = base_date.strftime('%y%m%d')
        current_user_num = 1
        current_research_num = 1
        
        # Dictionary to keep track of created accounts
        email_to_user_id = {}
        
        # Process the data in batches
        for i in range(0, len(df), batch_size):
            try:
                batch = df.iloc[i:i + batch_size]
                
                for _, row in batch.iterrows():
                    try:
                        # Create author account if doesn't exist
                        author_names = row['Author Full Names'].split('; ')
                        author_ids = []
                        
                        # Use a set to keep track of processed authors for this research
                        processed_authors = set()
                        
                        for author_name in author_names:
                            # Clean and format author name
                            clean_name = author_name.strip()
                            if not clean_name:
                                continue
                                
                            # Split name into first and last
                            name_parts = clean_name.split(', ')
                            if len(name_parts) < 2:
                                continue
                                
                            last_name = name_parts[0]
                            first_name = name_parts[1].split()[0]  # Take first word as first name
                            
                            # Create email from name
                            email = f"{first_name.lower()}.{last_name.lower()}@live.mcl.edu.ph"
                            
                            # Get or create user_id
                            if email in email_to_user_id:
                                user_id = email_to_user_id[email]
                            else:
                                # Check if account exists in database
                                account = Account.query.filter_by(email=email).first()
                                if account:
                                    user_id = account.user_id
                                else:
                                    # Create new account with formatted ID
                                    if current_user_num > 999:
                                        base_date = base_date + timedelta(days=1)
                                        current_date_str = base_date.strftime('%y%m%d')
                                        current_user_num = 1
                                    
                                    user_id = f'US-{current_date_str}-{current_user_num:03d}'
                                    current_user_num += 1
                                    
                                    account = Account(
                                        user_id=user_id,
                                        email=email,
                                        user_pw=generate_password_hash("1234"),
                                        role_id="06",
                                        acc_status="ACTIVE"
                                    )
                                    db.session.add(account)
                                    
                                    profile = UserProfile(
                                        researcher_id=user_id,
                                        first_name=first_name,
                                        last_name=last_name,
                                        college_id=random.choice(college_ids),
                                        program_id=random.choice(program_ids)
                                    )
                                    db.session.add(profile)
                                    email_to_user_id[email] = user_id
                            
                            # Only add user_id if we haven't processed this author yet
                            if user_id not in processed_authors:
                                author_ids.append(user_id)
                                processed_authors.add(user_id)
                        
                        if not author_ids:  # Skip if no valid authors
                            continue
                        
                        # Increment counter and date if needed for research ID
                        if current_research_num > 999:
                            base_date = base_date + timedelta(days=1)
                            current_date_str = base_date.strftime('%y%m%d')
                            current_research_num = 1
                        
                        research_id = f'RP-{current_date_str}-{current_research_num:03d}'
                        current_research_num += 1
                        
                        philippine_tz = pytz.timezone('Asia/Manila')
                        current_datetime = datetime.now(philippine_tz).replace(tzinfo=None)
                        
                        # Randomize year between 2011 and 2024
                        random_year = random.randint(2011, 2024)
                        # Randomize term between 1 and 3
                        random_term = str(random.randint(1, 3))
                        
                        research = ResearchOutput(
                            research_id=research_id,
                            college_id=random.choice(college_ids),
                            program_id=random.choice(program_ids),
                            title=row['Article Title'],
                            abstract=row['Abstract'],
                            research_type_id="FD",
                            date_uploaded=current_datetime,
                            user_id=author_ids[0],  # First author as uploader
                            adviser_id=random.choice(author_ids),  # Random author as adviser
                            school_year=str(random_year),  # Use random year
                            term=random_term  # Use random term
                        )
                        db.session.add(research)
                        db.session.flush()  # Flush to ensure research_id is available
                        
                        # Add authors (now guaranteed to be unique)
                        for idx, author_id in enumerate(author_ids, 1):
                            author = ResearchOutputAuthor(
                                research_id=research_id,
                                author_id=author_id,
                                author_order=idx
                            )
                            db.session.add(author)
                        
                        # Add research areas
                        if pd.notna(row['Research Areas']):
                            # Split research areas and remove duplicates using set()
                            research_areas = set(row['Research Areas'].split('; '))
                            for area in research_areas:
                                if area.strip():  # Only add non-empty areas
                                    # First, check if research area exists in reference table
                                    research_area = ResearchArea.query.filter_by(research_area_name=area.strip()).first()
                                    if not research_area:
                                        # Get the next available ID
                                        max_id = db.session.query(db.func.max(ResearchArea.research_area_id)).scalar()
                                        if max_id:
                                            # Extract the number from RA-XXX format
                                            current_num = int(max_id.split('-')[1])
                                            next_id = f'RA-{(current_num + 1):03d}'
                                        else:
                                            next_id = 'RA-001'
                                        
                                        # Create new research area with explicit ID
                                        research_area = ResearchArea(
                                            research_area_id=next_id,
                                            research_area_name=area.strip()
                                        )
                                        db.session.add(research_area)
                                        db.session.flush()  # Get the ID
                                    
                                    # Create research output area link
                                    research_output_area = ResearchOutputArea(
                                        research_id=research_id,
                                        research_area_id=research_area.research_area_id
                                    )
                                    db.session.add(research_output_area)
                        
                        # Add keywords
                        if pd.notna(row['Author Keywords']):
                            # Split keywords and remove duplicates using set()
                            keywords = set(row['Author Keywords'].split('; '))
                            for keyword in keywords:
                                if keyword.strip() and len(keyword.strip()) <= 100:
                                    kw = Keywords(
                                        research_id=research_id,
                                        keyword=keyword.strip()
                                    )
                                    db.session.add(kw)
                        
                        # Add random SDG
                        sdg = SDG(
                            research_id=research_id,
                            sdg=random.choice(sdg_list)
                        )
                        db.session.add(sdg)
                        
                        # Add random panel
                        panel = Panel(
                            research_id=research_id,
                            panel_id=random.choice(author_ids)  # Random author as panel
                        )
                        db.session.add(panel)
                        
                        # Flush after each research output and its related records
                        db.session.flush()
                        
                    except Exception as e:
                        print(f"Error processing row {total_processed}: {str(e)}")
                        db.session.rollback()
                        raise  # Re-raise the exception to trigger batch rollback
                
                # Commit batch
                db.session.commit()
                total_processed += len(batch)
                print(f"Processed {total_processed} records")
                
            except Exception as e:
                print(f"Error processing batch starting at index {i}: {str(e)}")
                db.session.rollback()
                raise  # Re-raise the exception to trigger full rollback
        
        return jsonify({
            "message": "Data population completed successfully",
            "total_processed": total_processed
        }), 200
        
    except Exception as e:
        db.session.rollback()
        error_msg = f"Error: {str(e)}"
        print(error_msg)
        return jsonify({"error": error_msg}), 500 