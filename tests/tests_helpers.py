def sign_in(client, user_id="test-user", name="Test User"):
    """Mark the test client as logged in without going through the login form."""
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["user_name"] = name
    return client
