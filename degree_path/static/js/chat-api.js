// Authentication comes from Flask's signed cookie, not Clerk on this page.
window.chatApiReady = Promise.resolve((function () {
  const userId = document.getElementById("account-navigation").dataset.userId;

  async function apiRequest(path, method, body) {
    const headers = { "X-App-User-ID": userId };
    if (method === "POST") {
      headers["Content-Type"] = "application/json";
      headers["X-CSRF-Token"] = document.querySelector("[data-csrf]").dataset.csrf;
    }
    const response = await fetch(path, {
      method, headers, credentials: "same-origin",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "The request failed.");
    return result;
  }
  return {
    load: () => apiRequest("/api/chat", "GET"),
    send: message => apiRequest("/api/chat", "POST", { message }),
    isSignedIn: () => Boolean(userId),
    loadProgramFavorites: () => apiRequest("/api/program-favorites", "GET"),
    loadProgramFavorite: id => apiRequest(`/api/program-favorites/${id}`, "GET"),
    setProgramFavorite: (id, favorite) => apiRequest(`/api/program-favorites/${id}`, "POST", {favorite}),
    loadFavorites: () => apiRequest("/api/favorites", "GET"),
    setFavorite: (cipcode, favorite) =>
      apiRequest("/api/favorites", "POST", { cipcode, favorite }),
  };
})());
