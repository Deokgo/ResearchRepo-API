from config import Session

"""
Sample usage:


def get_accounts_by_status(status):
    # Create a session
    session = Session()

    try:
        # Execute the function using SELECT for returning rows
        result = session.execute(
            text("SELECT * FROM get_account_by_status(:status)"), 
            {'status': status}
        )

        # Process the result, assuming the function returns a list of tuples or dictionaries
        accounts = [row for row in result]
        return accounts
    finally:
        session.close()

"""