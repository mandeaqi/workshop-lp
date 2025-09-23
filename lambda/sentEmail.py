import json
import boto3
import os
from botocore.exceptions import ClientError

# Initialize the Boto3 SES client. It's good practice to do this
# outside of the handler function for better performance.
ses_client = boto3.client('ses', region_name=os.environ.get('AWS_REGION'))

def create_response(status_code, body_message):
    """A helper function to create a standardized API Gateway response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # Required for CORS
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST, OPTIONS'
        },
        'body': json.dumps({'message': body_message})
    }

def lambda_handler(event, context):
    # Handle CORS preflight "OPTIONS" request
    if event.get('httpMethod') == 'OPTIONS':
        return create_response(200, 'CORS preflight successful')

    # 1. Validate environment variables
    to_email = os.environ.get('TO_EMAIL_ADDRESS')
    from_email = os.environ.get('FROM_EMAIL_ADDRESS')

    if not to_email or not from_email:
        print("Error: Missing environment variables for email addresses.")
        return create_response(500, 'Internal server error: Configuration missing.')

    # 2. Parse and validate the incoming request body
    try:
        payload = json.loads(event.get('body', '{}'))
    except (json.JSONDecodeError, TypeError):
        print("Error: Invalid JSON in request body.")
        return create_response(400, 'Invalid request body.')

    name = payload.get('name')
    email = payload.get('email')
    subject = payload.get('subject')
    message = payload.get('message')

    if not all([name, email, subject, message]):
        return create_response(400, 'Missing required fields: name, email, subject, message.')
        
    # 3. Construct the email body
    html_body = f"""
        <html>
        <head></head>
        <body style="font-family: Arial, sans-serif; font-size: 16px; color: #333;">
            <h2>New Message from Your Website</h2>
            <p><strong>Name:</strong> {name}</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Subject:</strong> {subject}</p>
            <hr>
            <h3>Message:</h3>
            <p>{message.replace(os.linesep, '<br>')}</p>
        </body>
        </html>
    """
    
    text_body = f"""
        New Message from Your Website\n
        Name: {name}\n
        Email: {email}\n
        Subject: {subject}\n
        -----------------------\n
        Message:\n
        {message}
    """

    # 4. Send the email using SES
    try:
        response = ses_client.send_email(
            Destination={
                'ToAddresses': [to_email],
            },
            Message={
                'Body': {
                    'Html': {'Charset': 'UTF-8', 'Data': html_body},
                    'Text': {'Charset': 'UTF-8', 'Data': text_body},
                },
                'Subject': {
                    'Charset': 'UTF-8',
                    'Data': f"New Contact Form Submission: {subject}",
                },
            },
            Source=from_email,
            ReplyToAddresses=[email], # Allows you to reply directly to the user
        )
        print(f"Email sent! Message ID: {response['MessageId']}")
        return create_response(200, 'Message sent successfully!')
        
    except ClientError as e:
        print(f"Error sending email: {e.response['Error']['Message']}")
        return create_response(500, 'Failed to send message.')