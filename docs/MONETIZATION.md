# Monetization

> Cards, crypto, the payment page, plans with subscriptions and discounts, transactions and refunds: see [PAYMENTS.md](PAYMENTS.md).
> Ad posts sent to all bot users (the **Ads** tab, Telegram-style editor, deleting posts from chats): see the Ads section below.

Four income sources, each switched on separately in the admin dashboard (**Monetization** page). Everything is off
after an update, so nothing changes for users until the owner turns a source on and presses **Save changes**.

| Source | What users see | Where the money goes |
|---|---|---|
| Premium | ⭐ Premium button in the bot menu: plans paid in Telegram Stars | The bot's Stars balance in @BotFather |
| Invite friends | A personal invite link on the ⭐ Premium screen | More users; Premium days are the reward |
| Required channel | "Join the channel" before the first download | Ad posts sold in your channel |
| Sponsored messages | A short ad under the download status message | Advertisers you sell the slot to |

## Premium (Telegram Stars)

- **Plans:** up to 6, each with days and a price in Stars. Defaults: 30 days for 100 ⭐, 90 days for 250 ⭐ and 365 days for 900 ⭐.
  The page shows the approximate payout, about $0.013 per Star.
- **Free plan limits:**
  - highest free quality (720p by default);
  - largest free file (200 MB by default);
  - free downloads per day, set in **Settings → Limits**.
- **What Premium gives:**
  - unlimited downloads (the bot-wide daily limit still protects the server);
  - every quality, including HD and 4K;
  - files up to the server limit;
  - its own queue, which workers always serve first;
  - no sponsored messages;
  - optionally, no required channel.
- **How a purchase works:**
  1. The user taps ⭐ Premium, picks a plan and pays in the Telegram payment window.
  2. Before charging, the server checks the plan is still on sale at that price.
  3. After payment, the days are added to the user's end date.
  4. Each Telegram charge id is stored, so a payment can never be counted twice.
- **Premium is shared across all three bots,** because it is stored on the shared user.
- **Withdrawing Stars:** open @BotFather → your bot → *Balance*. Stars become withdrawable 21 days after a purchase
  (Telegram's rule). Each bot has its own balance.
- **Manual Premium:** on **Users → Details** an administrator can gift Premium days or remove Premium. Use this for support,
  giveaways or a failed activation. If activation fails, the bot logs `premium_activation_failed` with the charge id.

## Invite friends

- **The link:** every user's link is `t.me/<bot>?start=ref_<user id>`. It appears on the ⭐ Premium screen with a Share button.
- **When an invite counts:** only for a person who is new to the whole platform, and only after their **first successful
  download or upload**. Self-invites and empty sign-ups earn nothing.
- **The reward:** every *N* counted friends give the inviter *D* days of Premium. *N* and *D* are set on the page,
  with defaults of 3 friends for 7 days.
- **Notifications:** the inviter gets a message for each friend ("1 of 3") and for each reward.

## Required channel

1. Enter the channel as `@username`, as a `t.me/...` link, or for a private channel as its `-100…` id plus an invite link.
2. Add **each bot** to the channel as an **administrator**. Telegram only lets admins check members.
3. Press **Check bots**. Every bot should show "admin ✓".

How it behaves for users:

- A new link or file triggers the "Join the channel" message, with a join button and an "I've joined" button.
- A positive check is remembered for 10 minutes.
- If a bot cannot check (it is not an admin, or the channel is wrong), users are let through and the bot logs a warning.
  A setup mistake never blocks the service.

## Sponsored messages

- **Contents:** each ad has a text (up to 300 characters) and an optional button with an `https://` link.
- **Display:**
  - one ad per download, chosen evenly and kept the same on retries;
  - shown under the status message while the file is being prepared, and removed with that message;
  - never shown to Premium users.
- **Views:** the page counts them per ad, one view per download that showed it.

## Ad posts (Ads tab)

How to write a post:
- **Editor:** like Telegram's — bold, italic, underline, strikethrough, spoiler, monospace, code block, link and quote, with Telegram Desktop's shortcuts.
- **Extras:** an optional photo and link button.
- **Preview and test:** a live preview, and a test send to your own Telegram ID.

How it is sent:
- Each person gets the post once, through the first selected bot they use.
- Premium users can be skipped, because Premium is ad-free.
- Sending runs in the background at about 25 messages a second, with live progress. A restarted worker never sends twice.
- The server rebuilds the post's markup from an allow-list, so nothing but Telegram formatting reaches users.

**Delete from chats** removes the post from every chat it reached. Telegram lets a bot delete its own messages only within 48 hours of sending; the dashboard explains this after that window.

## Technical notes

- **Settings:** stored in `system_settings` under the key `monetization` (`backend/services/monetization.py`).
- **Database:** migration `0002` adds `users.premium_until`, `users.referred_by` and `users.referral_counted`,
  and the ledger table `premium_payments`.
- **Bots:** they receive `pre_checkout_query` updates. Invoices use the currency `XTR` (Stars), which needs no payment provider.
- **Workers:** they consume the queues `priority,celery` in that order (`queue_order_strategy: priority`).
- **Applying the update:**
  1. `docker compose up -d --build` runs the migration.
  2. Restart the workers so they listen to the Premium queue.
