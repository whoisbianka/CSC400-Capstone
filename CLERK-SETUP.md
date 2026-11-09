# Connect Clerk

Set `CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY` in the server's private `.env` beside `app.py`. Set `CLERK_AUTHORIZED_PARTIES` to the comma-separated list of origins that serve the app. Flask passes the publishable key to the shared navigation, where `account-auth.js` reads it when loading Clerk.

## Verify locally

Run Flask as described in the README. Check that the homepage links open the questionnaire and Explore for guests. Select Sign in in the navigation, complete authentication, and confirm that the current page reloads with the signed-in navigation. Check Profile and sign out.

## Account data

Flask verifies the Clerk token at `/api/auth/session` and uses the verified account ID to scope saved majors, favorite programs, and account chat.

For production, configure a Clerk production instance and domain, use its production keys, and serve over HTTPS. Keep the secret key on the server.

## References

- [JavaScript quickstart](https://clerk.com/docs/js-frontend/getting-started/quickstart)
- [Sign-in component](https://clerk.com/docs/js-frontend/reference/components/authentication/sign-in)
- [Production deployment](https://clerk.com/docs/guides/development/deployment/production)
