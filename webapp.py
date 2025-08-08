from flask import Flask, request, render_template_string
import zarinpal
import config

app = Flask(__name__)

# A simple HTML template to display messages to the user
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Payment Status</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }
        .container { padding: 20px; border: 1px solid #ccc; display: inline-block; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ message }}</h1>
        <p>You can now return to the Telegram bot.</p>
    </div>
</body>
</html>
"""

@app.route('/verify', methods=['GET'])
def handle_verification():
    """
    This is the callback URL that Zarinpal will redirect the user to.
    It receives the payment status and authority, and verifies the transaction.
    """
    status = request.args.get('Status')
    authority = request.args.get('Authority')

    if not status or not authority:
        message = "Invalid callback request. Status or Authority missing."
        return render_template_string(HTML_TEMPLATE, message=message), 400

    # Verify the payment using our zarinpal module
    verification_message = zarinpal.verify_payment(status, authority)

    # Display the result to the user
    return render_template_string(HTML_TEMPLATE, message=verification_message)

@app.route('/app')
def mini_app():
    """Serves the main Mini App page, populated with plans from config."""
    return render_template('upgrade.html', plans=config.PRICING)

if __name__ == '__main__':
    # This is for local testing only.
    # In production, you should use a WSGI server like Gunicorn.
    app.run(port=5001)
