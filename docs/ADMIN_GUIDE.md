# Admin guide: earning with the bots

A step-by-step guide for the owner, covering everything in the dashboard that makes money or talks to users.
Every source of income starts **switched off**. Nothing changes for users until you switch something on and press **Save changes**.

Contents:
1. [Languages](#1-languages)
2. [Premium plans and prices](#2-premium-plans-and-prices)
3. [Payments: Stars, cards, crypto](#3-payments-stars-cards-crypto)
4. [A separate domain for links and payments](#4-a-separate-domain-for-links-and-payments)
5. [Invite friends](#5-invite-friends)
6. [Required channel](#6-required-channel)
7. [Ads under downloads](#7-ads-under-downloads)
8. [Ad posts to all users (Ads tab)](#8-ad-posts-to-all-users-ads-tab) · [The bots' public channel](#the-bots-public-channel-channel-tab)
9. [Users: gift or remove Premium](#9-users-gift-or-remove-premium)
10. [Withdrawing money](#10-withdrawing-money)
11. [Quick start checklist](#11-quick-start-checklist)

---

## 1. Languages

The bots and the dashboard speak 11 languages:

| | | | |
|---|---|---|---|
| English | Chinese | Hindi | Spanish |
| Arabic | French | Bengali | Portuguese |
| Russian | Urdu | Hebrew | |

- **Users** get their Telegram language automatically and can change it with 🌐 Language. Every language has a flag.
- **Dashboard:** change the language with the flag menu at the top. Arabic, Urdu and Hebrew are shown right-to-left.
- **Default bot language:** Settings → Limits → *Default bot language*. It is used when a user's language is not supported.

## 2. Premium plans and prices

**Monetization → Premium for Telegram Stars**

1. Turn the section **On**.
2. Set up your plans. Each plan card has:

   | Field | What it does |
   |---|---|
   | Switch | the plan is on sale or hidden |
   | Plan type | **One-time** (any number of days) or **Subscription · every 30 days** |
   | Days | how long Premium lasts (a subscription is always 30 days) |
   | Price, Stars | 1–10,000 ⭐ (Telegram's limit) |
   | Price, $ | price for cards and crypto on the payment page (empty = Stars only) |
   | Discount, % | applies to both prices; users see the final price and «-20%» |
   | Name / Badge | optional, e.g. «Monthly» and «🔥 Best value» |

   The grey box under each plan shows exactly what users will see, and roughly how much you receive per sale.

3. **Free plan limits:** free downloads per day, the highest free quality (e.g. 720p) and the largest free file. Above these limits users see a ⭐ mark and an offer to buy Premium.
4. **Optional:** a picture for the Telegram payment window.
5. Press **Save changes**.

What Premium gives users:
- unlimited downloads;
- HD/4K and large files;
- a faster queue;
- no ads;
- optionally, no required channel.

About **subscriptions**: Telegram charges the user automatically every 30 days, and each renewal adds 30 days of Premium. Users cancel in Telegram → Settings → My Stars.

## 3. Payments: Stars, cards, crypto

**Payments** tab.

### Telegram Stars
Switch it **On**. Users pay right inside the bot. Nothing else to set up.

### Cards and crypto
Each has its own section.

1. **Switch it On.** The «💳 Bank card» / «🪙 Crypto» button appears in the bots right away. Until a provider is connected, the button opens a «coming soon» page that offers Stars instead.
2. **Choose the provider:**
   - Cards: Stripe, ЮKassa, CloudPayments or PayPal.
   - Crypto: CryptoBot, NOWPayments, CoinGate or your own TON wallet.

   Providers marked «fields only» can already be filled in; they start working after the next update.
3. **Click «Where to get the keys»**, copy the keys from the provider's site and paste them into the fields.
4. **Copy the Webhook URL** and add it in the provider's dashboard. For Stripe, also select the events listed under the field.
5. **Press Save changes, then Test.** The badge turns green: **Connected**.
6. **Set a $ price** on each plan (Monetization → Plans → *Price, $*).

**What the user sees:** Premium → plan → «How to pay». They pick Stars right in the chat, or a card or crypto button that opens the payment page. They pay on the provider's site and come back to the bot, which then confirms: «Premium is active until …».

Premium is switched on **only** after the provider confirms the payment. Simply opening the «success» page does nothing.

### Transactions and revenue
- **Revenue:** income per payment method for today, 7 days, 30 days and all time.
- **Transactions:** every payment with its status (Pending, Paid, Failed, Expired, Refunded). Filter by status or method.
- **Refund:** returns the money through the provider and removes the Premium days. Crypto is refunded manually from your wallet.

### Keys are safe
Saved keys are never shown again; you see only a mask like `sk_tes…mnop`.
- To keep a key, leave the field empty.
- To delete it, press **Remove**.

## 4. A separate domain for links and payments

Use this so users never see your main domain.

1. Buy a short neutral domain. Optionally, put it behind Cloudflare to hide the server's IP.
2. In Plesk, add the domain, issue a Let's Encrypt certificate and paste the nginx block from `infrastructure/plesk/files.nginx.conf` (port 18000 on our server). The block opens only file links, the payment page and webhooks.
3. **Payments → Domain for links and the payment page:** enter `https://your-domain` and save.

From then on, file links, the payment page and webhook URLs use this domain.

## 5. Invite friends

**Monetization → Invite friends**
- Turn it **On**, then set how many friends earn a reward and how many Premium days it gives (e.g. 3 friends → 7 days).
- Each user finds their personal link and a Share button under ⭐ Premium.
- A friend counts only when they are new and have **downloaded something**, so fake sign-ups earn nothing.
- The inviter gets a message for each friend and for each reward.

## 6. Required channel

**Monetization → Required channel**

1. In Telegram, add **every bot** to your channel as an **administrator**.
2. Enter the channel as `@username` or a `t.me/…` link. For a private channel, enter its `-100…` id and an invite link.
3. Press **Check bots**. Every bot should show «admin ✓».
4. Optionally, let Premium users skip the channel.
5. **Several channels:** press **+ Add another channel** (up to 10). Users must join all of them; the bot shows a
   numbered Join button for each channel they have not joined yet.

Users see «Join the channel» with a join button and an «I've joined» button before their first download. If a bot can't check (for example, it isn't an admin), users are let through, so the service never breaks.

## 7. Ads under downloads

**Monetization → Sponsored messages**

- **Setting it up:** turn it On and add ads, each with a text and an optional button and link. You can switch each ad on or off separately.
- **What users see:** while a file is being prepared, a short ad appears under the status message and disappears with it.
- **Who sees it:** one ad per download. Premium users never see ads.
- **Views:** counted for each ad.

## 8. Ad posts to all users (Ads tab)

Send a post to your bots' users, like a channel post.

1. **Write the post** in the editor. The toolbar (or the same shortcuts as Telegram Desktop) gives:

   | Formatting | Shortcut |
   |---|---|
   | **Bold** | Ctrl+B |
   | *Italic* | Ctrl+I |
   | Underline | Ctrl+U |
   | ~~Strikethrough~~ | Ctrl+Shift+X |
   | Spoiler | Ctrl+Shift+P |
   | Monospace | Ctrl+Shift+M |
   | Link | Ctrl+K |
   | Quote | Ctrl+Shift+. |
   | Clear formatting | Ctrl+Shift+N |

   The code block button has no shortcut.
2. **Optional:** add a photo and a button with a link.
3. **Choose the bots** (all connected bots by default). Each person gets the post **once**, even if they use several bots. Premium users can be skipped.
4. **Test it:** enter your Telegram ID (ask @userinfobot), press **Send test** and check how it looks.
5. **Publish:** press **Publish to N**. Progress updates live.

**Sent posts** shows each post's audience and how many messages were delivered, not delivered and removed.
- **Delete from chats** removes the post from everyone who got it. Telegram allows this only within **48 hours** of sending.
- **Use again** loads the post back into the editor.

### The bots' public channel (Channel tab)

Run your public channel from the dashboard.

1. In Telegram, add one bot to the channel as an **administrator** with the rights to post, edit, delete and pin.
2. **Channel → Connect the channel:** enter `@username` (or a `t.me/…` link or the `-100…` id), choose that bot and press
   **Save and check**. A green lamp, the channel's title, its subscribers and the bot's rights appear (a red ✕ shows a
   missing right).
3. **New post:** text with formatting, a photo or an MP4 video (up to 50 MB), up to 6 link buttons. The preview on the
   right shows it as Telegram will.
4. Choose **Now** or **At a set time** and press **Publish now** / **Schedule**. Scheduled posts go out on their own.
5. **Channel posts** lists everything: **Edit** (changes the post in the channel too), **Pin / Unpin**,
   **Publish now** (for scheduled or failed posts), **Open in Telegram**, **Delete from channel**. A failed post shows
   Telegram's reason (for example, a missing right).

Telegram does not give bots the number of views of a post, so views are not shown in the dashboard.

## 9. Users: gift or remove Premium

**Users → Details**
- Shows Premium status and its end date.
- **Gift Premium** adds any number of days, for support, partners or giveaways.
- **Remove Premium** takes it away.

A ⭐ Premium badge marks Premium users in the list.

## 10. Withdrawing money

**Stars:**
1. Open @BotFather → `/mybots` → your bot → **Balance** → **Withdraw**.
2. On Fragment, connect a TON wallet. The Stars arrive there as Toncoin.

Stars can be withdrawn about 21 days after each purchase. Each bot has its own balance. Instead of withdrawing, you can also spend Stars on Telegram Ads.

**Cards and crypto:** the money goes to your account at the provider (Stripe, CryptoBot, …) and is withdrawn there.

## 11. Quick start checklist

- [ ] Monetization: Premium **On**, plans and prices set, free limits set → **Save changes**
- [ ] Payments: Telegram Stars **On**
- [ ] Payments: card and/or crypto provider chosen, keys entered, webhook added, **Test** is green
- [ ] Plans: a **$ price** set for card and crypto
- [ ] (Optional) neutral domain added in Plesk and in Payments
- [ ] (Optional) Invite friends, required channel, ads
- [ ] In the bot: ⭐ Premium shows your plans, and a test purchase works

> **Telegram's rule:** inside bots, digital goods are expected to be paid in Telegram Stars. Card and crypto payments through an outside page work, but they carry some risk of restrictions from Telegram. Keep Stars as the main option.
