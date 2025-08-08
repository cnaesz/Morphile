# zarinpal.py
import requests
import config
from database import create_pending_payment, get_and_delete_pending_payment, set_premium

def create_payment_link(amount: int, user_id: int, plan: str):
    """
    Creates a payment link and stores the pending transaction in the database.
    """
    request_data = {
        "MerchantID": config.ZARINPAL_MERCHANT,
        "Amount": amount,
        "CallbackURL": config.ZARINPAL_CALLBACK,
        "Description": f"Purchase of {plan} for user {user_id}",
    }
    try:
        res = requests.post("https://api.zarinpal.com/pg/v4/payment/request.json", json=request_data)
        res.raise_for_status()
        response_data = res.json()
        authority = response_data.get("data", {}).get("authority")

        if authority:
            # Save the pending payment to the database
            create_pending_payment(authority, user_id, plan, amount)
            return f"https://www.zarinpal.com/pg/StartPay/{authority}"
    except requests.exceptions.RequestException as e:
        print(f"Error creating payment link: {e}")
        return None
    return None

def verify_payment(status: str, authority: str):
    """
    Verifies a payment with Zarinpal's servers.
    If successful, it grants premium status to the user.
    """
    if status != "OK":
        return "Payment was cancelled by the user."

    # Retrieve and delete the pending payment to prevent reuse
    pending_payment = get_and_delete_pending_payment(authority)
    if not pending_payment:
        return "Payment not found or already processed."

    user_id = pending_payment['user_id']
    amount = pending_payment['amount']
    plan_name = pending_payment['plan']

    # --- Verify the transaction with Zarinpal ---
    verify_data = {
        "MerchantID": config.ZARINPAL_MERCHANT,
        "Amount": amount,
        "Authority": authority,
    }
    try:
        res = requests.post("https://api.zarinpal.com/pg/v4/payment/verify.json", json=verify_data)
        res.raise_for_status()
        response_data = res.json().get("data", {})

        # Check if the payment was successful (code 100)
        if response_data.get("code") == 100:
            # --- Grant Premium Status ---
            plan_details = config.PRICING.get(plan_name)
            if not plan_details:
                return f"Error: Plan '{plan_name}' not found."

            set_premium(user_id, plan_details['duration_days'], plan_details['limit'])
            # You might want to save the transaction reference (ref_id) here
            # payments.insert_one({...})
            return f"✅ Payment successful! Your premium plan '{plan_name}' is now active."
        else:
            return f"❌ Payment failed. Status code: {response_data.get('code')}"

    except requests.exceptions.RequestException as e:
        print(f"Error verifying payment: {e}")
        return "An error occurred during verification. Please contact support."