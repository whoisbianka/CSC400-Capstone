window.chatApiReady = (async function () {
  const key = window.CLERK_PUBLISHABLE_KEY;

  if (!key) {
    throw new Error("Clerk publishable key is missing.");
  }

  // Clerk publishable keys contain the frontend API domain.
  const encodedDomain = key.split("_")[2];
  const domain = atob(encodedDomain).replace(/\$$/, "");

    await new Promise((resolve, reject) => {
    const script = document.createElement("script");

    const timeout = window.setTimeout(() => {
        script.onload = null;
        script.onerror = null;
        script.remove();

        reject(
        new Error("Sign-in services took too long to load. Please reload.")
        );
    }, 20000);

    script.src =
        `https://${domain}/npm/@clerk/clerk-js@6/dist/clerk.browser.js`;

    script.crossOrigin = "anonymous";
    script.setAttribute("data-clerk-publishable-key", key);

    script.onload = () => {
        window.clearTimeout(timeout);
        resolve();
    };

  script.onerror = () => {
    window.clearTimeout(timeout);
    script.remove();

    reject(
      new Error("Unable to load sign-in services. Please reload.")
    );
  };

  document.head.appendChild(script);
});

  await window.Clerk.load();

  async function chatRequest(method, body) {
    const headers = {};

    // Check the active session for every request.
    if (window.Clerk.session) {
      const token = await window.Clerk.session.getToken();

      if (!token) {
        throw new Error("Please sign in again.");
      }

      headers.Authorization = `Bearer ${token}`;
    }

    if (method === "POST") {
      headers["Content-Type"] = "application/json";
      headers["X-CSRF-Token"] =
        document.getElementById("guided-chat").dataset.csrf;
    }

    const response = await fetch("/api/chat", {
      method,
      headers,
      credentials: "same-origin",
      body: body ? JSON.stringify(body) : undefined,
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "The chat request failed.");
    }

    return result;
  }

  return {
    load: () => chatRequest("GET"),
    send: (message) => chatRequest("POST", { message }),
  };
})();