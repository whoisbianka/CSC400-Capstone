(async function () {
  "use strict";

  const messages = document.getElementById("chatMessages");
  const input = document.getElementById("userInput");
  const sendButton = document.getElementById("sendButton");
  const status = document.getElementById("chatStatus");
  const storageNote = document.getElementById("chatStorageNote");
  const reloadButton = document.getElementById("reloadChat");
  const recommendationsPanel =document.getElementById("recommendationsPanel");
  const recommendationCards =document.getElementById("recommendationCards");

  let api = null;
  let busy = false;
  const resetChatButton = document.getElementById("resetAdvisorChat");

  const favoriteIds = new Set();
  let favoritesLoaded = false;

  function createFavoriteButton(cipcode) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "recommendation-heart";

    function updateLabel() {
      const saved = favoriteIds.has(cipcode);

      button.setAttribute("aria-pressed", String(saved));

      const label = !api.isSignedIn() ? "Sign in to favorite"
        : !favoritesLoaded ? "Favorites unavailable"
        : saved ? "Remove favorite" : "Favorite major";
      button.textContent = saved ? "♥" : "♡";
      button.setAttribute("aria-label", label);
      button.title = label;
      button.disabled = api.isSignedIn() && !favoritesLoaded;
    }

    updateLabel();

    button.addEventListener("click", async () => {
      if (!api.isSignedIn()) {
        setStatus("Sign in using your account, then reload this page.");
        return;
      }

      const shouldFavorite = !favoriteIds.has(cipcode);
      button.disabled = true;

      try {
        const result = await api.setFavorite(
          cipcode,
          shouldFavorite
        );

        if (result.favorite) {
          favoriteIds.add(cipcode);
        } else {
          favoriteIds.delete(cipcode);
        }

        updateLabel();

        setStatus(
          result.favorite
            ? "Major added to your favorites."
            : "Major removed from your favorites."
        );
      } catch (error) {
        setStatus(error.message || "Unable to update favorites.");
      } finally {
        button.disabled = false;
      }
    });

    return button;
  }

  function setStatus(message) {
    status.textContent = message;
  }

  function setBusy(value) {
    busy = value;

    input.disabled = value;
    sendButton.disabled = value;

    messages.setAttribute("aria-busy", String(value));
    resetChatButton.disabled = value;
  }

  function showStorageNote(mode) {
    if (mode === "user") {
      storageNote.textContent =
        "Your chat and interests are saved to your account.";
    } else {
      storageNote.textContent =
        "Guest chat is saved temporarily in this browser's session. " +
        "It expires 24 hours after the last successful message.";
    }
  }

  function addMessage(role, content) {
    const bubble = document.createElement("div");

    bubble.className =
      role === "user" ? "user-message" : "bot-message";

    const label = document.createElement("strong");

    label.textContent =
      role === "user" ? "You:" : "Degree Path Explorer:";

    const text = document.createElement("span");

    // Treat user and Gemini output as text, never executable HTML.
    text.textContent = content;
    text.style.whiteSpace = "pre-wrap";

    bubble.append(
      label,
      document.createElement("br"),
      text
    );

    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
  }

  function renderHistory(history) {
    messages.replaceChildren();

    if (history.length === 0) {
      addMessage(
        "assistant",
        "Hi! I can help you explore majors based on your interests. " +
        "What subjects or activities do you enjoy?"
      );

      return;
    }

    for (const message of history) {
      addMessage(message.role, message.content);
    }
  }

  function renderRecommendations(recommendations) {
    recommendationCards.replaceChildren();

    recommendationsPanel.hidden = recommendations.length === 0;

    for (const recommendation of recommendations) {
      const card = document.createElement("article");
      card.className = "major-recommendation";

      const title = document.createElement("h3");
      const majorLink = document.createElement("a");
      majorLink.href = "/majors/" + Number(recommendation.cipcode);
      majorLink.textContent = recommendation.major;
      title.appendChild(majorLink);

      const count = document.createElement("p");

      const number = recommendation.matching_keywords;
      count.textContent =
        `${number} matching ${number === 1 ? "interest" : "interests"}`;

      const favoriteButton = createFavoriteButton(Number(recommendation.cipcode));
      card.append(title, count, favoriteButton);

      recommendationCards.appendChild(card);
    }
  }
  async function sendMessage() {
    if (busy || api === null) {
      return;
    }

    const message = input.value.trim();

    if (!message) {
      setStatus("Enter a message first.");
      input.focus();
      return;
    }

    if (message.length > 4000) {
      setStatus("Please keep your message under 4,001 characters.");
      input.focus();
      return;
    }

    reloadButton.hidden = true;
    setBusy(true);
    setStatus("The advisor is thinking…");

    try {
      const result = await api.send(message);

      // Display the exchange after the server confirms it was saved.
      addMessage("user", message);
      addMessage("assistant", result.reply);

      input.value = "";

      showStorageNote(result.mode);
      renderRecommendations(result.recommendations ?? []);
      setStatus("");
    } catch (error) {
      // Keep the typed message so the user does not lose it.
      setStatus(
        error instanceof Error
          ? error.message
          : "Unable to send your message. Please try again."
      );

      reloadButton.hidden = false;
    } finally {
      setBusy(false);
      input.focus();
    }
  }

  resetChatButton.addEventListener('click', async () => {
    if (busy || !api) return;
    if (!window.confirm('Remove your chat, saved interests, and recommendations? Favorites and preferences will be kept.')) return;
    setBusy(true);
    setStatus('Resetting your chat…');
    try {
      await api.resetChat();
      input.value = '';
      renderHistory([]);
      renderRecommendations([]);
      reloadButton.hidden = true;
      setStatus('Chat reset. Tell me what subjects or activities you enjoy.');
    } catch (error) { setStatus(error.message); }
    finally { setBusy(false); }
  });

  sendButton.addEventListener("click", sendMessage);

  input.addEventListener("keydown", (event) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.isComposing
    ) {
      event.preventDefault();
      sendMessage();
    }
  });

  reloadButton.addEventListener("click", () => {
    window.location.reload();
  });

  // Recover this visitor's saved conversation using the Flask session.
  setBusy(true);

  try {
    if (!window.chatApiReady) {
      throw new Error(
        "The chat API did not load. Please reload the page."
      );
    }

    api = await window.chatApiReady;

    const saved = await api.load();
    let favoritesWarning = "";

    if (api.isSignedIn()) {
      try {
        const result = await api.loadFavorites();

        for (const favorite of result.favorites) {
          favoriteIds.add(Number(favorite.cipcode));
        }

        favoritesLoaded = true;
      } catch (error) {
        favoritesWarning =
          "Chat loaded, but favorites could not load. Reload to retry.";
      }
    }

    renderHistory(saved.messages);
    showStorageNote(saved.mode);
    renderRecommendations(saved.recommendations ?? []);

    setStatus(favoritesWarning);
    setBusy(false);

    input.focus();
  } catch (error) {
    setStatus(
      error instanceof Error
        ? error.message
        : "Unable to load your chat. Please reload the page."
    );

    messages.setAttribute("aria-busy", "false");

    // Keep sending disabled if initialization failed.
    reloadButton.hidden = false;
  }
})();