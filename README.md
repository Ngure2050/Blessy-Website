# Blessy Suppliers

## Run the website

```powershell
py -m pip install -r requirements.txt
py app.py
```

Open `http://127.0.0.1:5000`.

## Orders and WhatsApp

Submitted orders are saved locally in `instance/orders.db`. The confirmation page opens WhatsApp with a pre-filled order message for `0759924416`; the user taps **Send** in WhatsApp.

## Admin dashboard

Set an admin password before starting the app, then visit `http://127.0.0.1:5000/admin/orders`.

```powershell
$env:ADMIN_PASSWORD = "choose-a-strong-password"
$env:ADMIN_USERNAME = "admin"
py app.py
```

The browser will prompt for this username and password. Do not commit a real password to the repository.
