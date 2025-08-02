# zarinpal.py
import requests
import config

def create_payment_link(amount, user_id, plan):
    data = {
        "MerchantID": config.ZARINPAL_MERCHANT,
        "Amount": amount,
        "CallbackURL": config.ZARINPAL_CALLBACK,
        "Description": f"اشتراک {plan} برای کاربر {user_id}",
        "Metadata": {"user_id": user_id, "plan": plan}
    }
    try:
        res = requests.post("https://api.zarinpal.com/pg/v4/payment/request.json", json=data)
        if res.status_code == 200:
            authority = res.json().get("Authority")
            return f"https://zarinp.al/{authority}" if authority else None
    except:
        pass
    return None