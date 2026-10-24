// Load Clerk only after an explicit account action (or its OAuth return).
(() => {
  const nav = document.getElementById("account-navigation");
  const status = document.getElementById("account-status");
  const retryLogout = document.getElementById("account-retry-logout");
  const pendingLogin = "degree-path-login-pending";
  const pendingLogout = "degree-path-logout-pending";
  let clerkPromise;
  let completing = false;
  let busy = false;

  function showStatus(message) {
    status.textContent = message;
    status.hidden = !message;
  }

  function loadScript(src, key) {
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      const timer = setTimeout(() => {
        script.remove();
        reject(new Error("Sign-in service took too long to load. Please retry."));
      }, 20000);
      script.src = src;
      script.crossOrigin = "anonymous";
      if (key) script.setAttribute("data-clerk-publishable-key", key);
      script.onload = () => { clearTimeout(timer); resolve(); };
      script.onerror = () => {
        clearTimeout(timer);
        script.remove();
        reject(new Error("Unable to load sign-in services. Please retry."));
      };
      document.head.appendChild(script);
    });
  }

  function loadClerk() {
    if (!clerkPromise) {
      clerkPromise = (async () => {
        const key = nav.dataset.clerkKey;
        const decoded = atob(key.split("_")[2]);
        const domain = decoded.slice(0, -1);
        if (!decoded.endsWith("$") || !/^[a-z0-9]+(?:[.-][a-z0-9]+)+$/i.test(domain)) {
          throw new Error("Invalid sign-in configuration.");
        }
        if (!window.__internal_ClerkUICtor) {
          await loadScript(`https://${domain}/npm/@clerk/ui@1/dist/ui.browser.js`);
        }
        if (!window.Clerk) {
          await loadScript(`https://${domain}/npm/@clerk/clerk-js@6/dist/clerk.browser.js`, key);
        }
        await window.Clerk.load({ui: {ClerkUI: window.__internal_ClerkUICtor}});
        return window.Clerk;
      })().catch(error => { clerkPromise = null; throw error; });
    }
    return clerkPromise;
  }

  async function post(path, token) {
    const headers = {"Content-Type": "application/json", "X-CSRF-Token": nav.dataset.csrf};
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await fetch(path, {
      method: "POST", credentials: "same-origin", headers, body: "{}",
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Account request failed. Please reload.");
    return result;
  }

  async function completeLogin(clerk) {
    if (completing || !clerk.session) return;
    completing = true;
    try {
      const token = await clerk.session.getToken();
      if (!token) throw new Error("Please sign in again.");
      await post("/api/auth/session", token);
      sessionStorage.removeItem(pendingLogin);
      clerk.closeSignIn();
      // Refresh this same page with the verified Flask user_id.
      window.location.reload();
    } catch (error) {
      completing = false;
      showStatus(error.message);
    }
  }

  let unsubscribe;
  async function signIn() {
    showStatus("Loading sign-in…");
    const clerk = await loadClerk();
    sessionStorage.setItem(pendingLogin, "1");
    if (clerk.session) {
      await completeLogin(clerk);
      return;
    }
    if (unsubscribe) unsubscribe();
    unsubscribe = clerk.addListener(({session}) => {
      if (session) void completeLogin(clerk);
    });
    showStatus("");
    // OAuth may visit the identity provider, but returns to this same URL.
    clerk.openSignIn({
      forceRedirectUrl: window.location.href,
      signUpForceRedirectUrl: window.location.href,
    });
  }

  async function signOut() {
    showStatus("Signing out…");
    sessionStorage.removeItem(pendingLogin);
    // Clear app access even if the external sign-out service is unavailable.
    await post("/logout");
    sessionStorage.setItem(pendingLogout, "1");
    try {
      const clerk = await loadClerk();
      await clerk.signOut();
      sessionStorage.removeItem(pendingLogout);
    } catch (_) {
      // The refreshed page offers a retry, without retaining app access.
    }
    window.location.reload();
  }

  document.querySelectorAll("[data-auth-action]").forEach(button => {
    button.addEventListener("click", async () => {
      if (busy) return;
      busy = true;
      button.disabled = true;
      try {
        if (button.dataset.authAction === "logout") await signOut();
        else await signIn();
      } catch (error) {
        showStatus(error.message);
      } finally {
        busy = false;
        button.disabled = false;
      }
    });
  });

  if (sessionStorage.getItem(pendingLogout)) {
    showStatus("You are signed out of this app. Clerk sign-out could not finish; please retry.");
    retryLogout.hidden = false;
  }
  retryLogout.addEventListener("click", async () => {
    retryLogout.disabled = true;
    try {
      const clerk = await loadClerk();
      await clerk.signOut();
      sessionStorage.removeItem(pendingLogout);
      retryLogout.hidden = true;
      showStatus("Signed out.");
    } catch (error) {
      showStatus(error.message);
    } finally {
      retryLogout.disabled = false;
    }
  });

  // A verified profile visit may load identity details; normal guest visits stay lazy.
  const profile = document.getElementById("profile-account");
  if (profile && nav.dataset.userId) {
    const clean = value => typeof value === "string" ? value.trim().slice(0, 200) : "";
    loadClerk().then(clerk => {
      const user = clerk.user;
      if (!clerk.session || !user || user.id !== profile.dataset.clerkUserId) {
        throw new Error("Your sign-in changed. Sign out and sign in again to refresh your account details.");
      }
      const name = clean(user.fullName) || [clean(user.firstName), clean(user.lastName)].filter(Boolean).join(" ") || clean(user.username);
      const email = clean(user.primaryEmailAddress?.emailAddress);
      document.getElementById("profile-name").textContent = name || "Your account";
      document.getElementById("profile-email").textContent = email || "Email address not provided";
      document.getElementById("profile-name-value").textContent = name || "Not provided";
      document.getElementById("profile-email-value").textContent = email || "Not provided";
      document.getElementById("profile-avatar").textContent = name ? name.split(/\s+/).slice(0, 2).map(part => part[0]).join("").toUpperCase() : "?";
    }).catch(error => {
      document.getElementById("profile-email").textContent = "Account details unavailable";
      document.getElementById("profile-name-value").textContent = "Unavailable";
      document.getElementById("profile-email-value").textContent = "Unavailable";
      document.getElementById("profile-identity-status").textContent = error.message;
    });
  }

  if (sessionStorage.getItem(pendingLogin) && !nav.dataset.userId) {
    // Finish an explicitly requested sign-in after an OAuth redirect.
    // Never open a modal automatically on normal guest visits.
    sessionStorage.removeItem(pendingLogin);
    loadClerk().then(clerk => completeLogin(clerk)).catch(error => showStatus(error.message));
  }
})();
