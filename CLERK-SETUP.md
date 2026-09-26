# Connect Clerk

The static site's profile page uses Clerk's JavaScript SDK and prebuilt sign-in/sign-up and profile components. College browsing stays public. No Clerk application is configured yet.

## Create your application

1. Create an account at https://dashboard.clerk.com and create an application named **Degree Path Explorer**.
2. Enable email authentication. For this student audience, email verification codes are a simple starting point. Keep phone numbers and other profile fields optional unless the product needs them. The dashboard controls which sign-in methods the embedded component offers.
3. Open **API keys** and copy the **Publishable key**, starting with `pk_test_` for development.
4. Paste it between the quotes in `assets/js/clerk-config.js`. This key is designed to be public. Never paste an `sk_test_` or `sk_live_` secret key into the site.
5. Serve this directory over HTTP using your existing local server (for example, VS Code Live Server), then open `profile.html`. Opening the file directly with `file://` will not work for authentication.
6. Create a test account, complete email verification, check profile editing, sign out, and sign back in. Also check a page reload and sign-out from a second tab.

## Before real student accounts

- Configure a Clerk production instance and its production domain following Clerk's deployment instructions; replace the development publishable key with the production publishable key. Host the app over HTTPS.
- Publish your actual privacy policy and terms and configure their URLs and any required acceptance in Clerk. The intended audience is 17–18-year-old high school juniors and seniors; this integration does not verify age or establish legal compliance. Decide separately whether younger students may register.
- Keep academic preferences and future saved colleges in your application database, linked to Clerk's user ID. This change only adds authentication/account management; it does not add storage for student preferences or saved colleges.
- When adding a backend, verify Clerk session tokens on the server and enforce ownership for every private record. Hiding content in this static page is not access control. Never trust a user ID supplied by the browser on its own.

## What to expect now

With an empty key, the profile page explains that accounts are not available yet. With a configured key, signed-out visitors get Clerk's combined sign-in/sign-up flow and signed-in visitors get account management plus sign-out. Script failures show a retry button. Only the profile page loads Clerk.

Clerk authentication handles account access. It does not automatically supply age verification, guardian consent, or a privacy policy for your application.

## References

- JavaScript quickstart: https://clerk.com/docs/js-frontend/getting-started/quickstart
- Sign-in component: https://clerk.com/docs/js-frontend/reference/components/authentication/sign-in
- User profile component: https://clerk.com/docs/js-frontend/reference/components/user/user-profile
- Production deployment: https://clerk.com/docs/guides/development/deployment/production
- Clerk privacy policy: https://clerk.com/legal/privacy
