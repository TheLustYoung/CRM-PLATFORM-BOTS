from backend.api import admin, auth, broadcasts, channel, health, internal, pay, payments, public, team

routers = [health.router, auth.router, admin.router, broadcasts.router, channel.router, payments.router, team.router, internal.router, public.router, pay.router]
