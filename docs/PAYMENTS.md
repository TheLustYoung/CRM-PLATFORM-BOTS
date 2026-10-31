# Payments

One billing system for all methods, each switched on and configured in the dashboard (**Payments** page).

## How a user pays

| Method | Where | How Premium is activated |
|---|---|---|
| Telegram Stars | inside the bot (invoice or subscription link) | `successful_payment` update, idempotent per Telegram charge id |
| 💳 Bank card | our payment page → the card provider chosen in the dashboard | the provider's **signed webhook** |
| 🪙 Crypto | our payment page → the crypto provider chosen in the dashboard | the provider's **signed webhook** |

1. **In the bot:** ⭐ Premium → plan → «How to pay»: Stars right there, or Card / Crypto buttons that open `https://<neutral domain>/pay/<token>`.
2. **On the payment page:** shown in the user's language. It redirects to the provider (Stripe Checkout, CryptoBot invoice, …), and the provider sends the user back to `/pay/<token>/done`.
3. **Activation:** only a webhook with a valid signature marks the order paid and grants the plan's days. The bot then writes «Premium is active until …».
   - The return page alone never activates anything; it waits for the webhook.
   - Repeated webhooks change nothing.
   - A payment that arrives after the link expired still counts.
4. **A method switched on before its provider is connected:** the button still works and the page says the method is coming soon, offering Stars.

## Plans (Monetization → Plans)

These are Telegram's own rules for Stars:
- **Price:** a whole number of Stars from 1 to 10,000.
- **Type:** a one-time plan for any number of days, or a **Telegram subscription** that Telegram renews every 30 days.
  - Telegram supports only this 30-day period for subscriptions.
  - Users cancel it in Telegram → Settings → My Stars.
  - Every renewal arrives as a new `successful_payment` and adds 30 days.
  - Subscriptions are Stars-only; cards and crypto are one-time.

Each plan also has:
- an on/off switch;
- a $ price for cards and crypto;
- a discount in % (applies to ⭐ and $);
- an optional name and badge.

Other settings on that page:
- an optional picture for the Stars invoice;
- free downloads per day.

## Providers

| Category | Provider | State |
|---|---|---|
| Card | Stripe | works: Checkout, signed webhooks, refunds |
| Card | ЮKassa, CloudPayments, PayPal | dashboard fields ready; module to be added |
| Crypto | CryptoBot (Crypto Pay API) | works: invoices in USD, paid in USDT/TON/BTC/…, signed webhooks |
| Crypto | NOWPayments, CoinGate, own TON wallet | dashboard fields ready; module to be added |

**Adding a provider:**
1. Write one file in `backend/services/payments/` with the functions:
   - `configured`
   - `price`
   - `checkout`
   - `refund`
   - `check`
   - `parse_webhook`
2. Point the `module` of the provider's catalog entry (in `payments/__init__.py`) at that file.

The bots, the payment page, the dashboard and the reports pick it up automatically.

**Secrets:**
- Provider keys are stored on the server and are never sent back to the browser; the dashboard shows only a masked hint.
- An empty field keeps the saved key, and the Remove button deletes it.

**Setting up a provider:**
1. Enter its keys and copy its webhook URL `https://<domain>/webhooks/<provider>` into the provider's dashboard.
2. For Stripe, subscribe to these events:
   - `checkout.session.completed`
   - `checkout.session.async_payment_succeeded`
   - `checkout.session.async_payment_failed`
   - `checkout.session.expired`
   - `charge.refunded`
3. Press **Test**.

## Neutral domain

Set it in **Payments → Domain for links and the payment page**. It is used for file links, the payment page and webhooks. In Plesk, use `infrastructure/plesk/files.nginx.conf`: it opens only `/f/`, `/pay/` and `/webhooks/` and returns 404 for everything else.

## Transactions and refunds

All payments are listed in one table (`orders`) with these statuses: pending, paid, failed, expired, canceled, refunded. Stars purchases and renewals are included.

**Refund** sends the money back through the provider — Stars through `refundStarPayment`, Stripe through the Refunds API — and removes the plan's days. Crypto invoices are refunded manually from the wallet.

**Revenue** is reported by method and currency for today, 7 days, 30 days and all time.

## Telegram rules

Telegram requires digital goods sold inside bots to be paid in Stars. Linking to an outside payment page for digital goods may break Telegram's rules for bots. Many bots do it, but there is a risk of restrictions. Keep Stars as the main option inside the bot.
