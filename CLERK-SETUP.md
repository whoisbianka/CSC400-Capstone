# Connect Clerk

Homepage cards lead to `/start/questionnaire` or `/start/explore`. Each page offers sign-in/create-account and a direct guest link. Clerk loads only after the sign-in button is selected, then opens a centered sign-up modal with a sign-in link for existing accounts. Successful authentication continues to the selected destination. An existing active session also continues there when the sign-in button is selected.

The public development publishable key is configured in `degree_path/static/js/clerk-config.js`. Authentication is implemented in `degree_path/static/js/start-auth.js`. Profile contains no Clerk components or scripts.

## Verify locally

Run Flask as described in README.md. Click each homepage card and check both choices. For sign-in, complete email verification and confirm that the selected questionnaire or explorer opens. Guest access must remain available if Clerk fails to load. Real sign-in and sign-up still need browser verification.

## Account data

Authentication does not save questionnaire answers or favorites. Flask routes do not yet verify Clerk sessions. Before adding private storage, verify session tokens on the server and enforce record ownership using the verified user identity.

Before production, configure a Clerk production instance and domain, use its public production key, serve over HTTPS, and configure the application's actual privacy policy and terms. Never place Clerk secret keys in browser code.

## References

- [JavaScript quickstart](https://clerk.com/docs/js-frontend/getting-started/quickstart)
- [Sign-in component](https://clerk.com/docs/js-frontend/reference/components/authentication/sign-in)
- [Production deployment](https://clerk.com/docs/guides/development/deployment/production)
