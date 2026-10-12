(() => {
  function escapeText(value) {
    const node = document.createElement('span');
    node.textContent = value;
    return node.innerHTML;
  }


  // Connect JavaScript to the chatbot elements
  const userInput = document.getElementById("userInput");
  const sendButton = document.getElementById("sendButton");
  const chatMessages = document.getElementById("chatMessages");

  // Keeps track of which core question the user is answering
  let currentQuestion = 0;

  // Keeps track of whether we are asking a follow-up question
  let followUpMode = false;

  // Stores the user's answers
  const userProfile = {
    name: "",
    interests: "",
    strengths: "",
    careerInterest: "",
    careerFollowUp: "",
    majorInterest: "",
    locationPreference: "",
    costImportance: ""
  };

  // Core questions
  const questions = [

    "What subjects or activities are you most interested in?",

    "What would you say are some of your strengths?",

    "Is there a career or field you're already interested in? It's okay if you're not sure yet.",

    "Do you already have a college major in mind? It's okay if you don't.",

    "For college location, would you prefer to stay in-state, go out-of-state, or do you have no preference?",

    "How important is keeping college costs low for you?"

  ];


  // Adds a bot message to the screen
  function addBotMessage(message) {

    const botMessage = document.createElement("div");

    botMessage.classList.add("bot-message");

    botMessage.innerHTML =
      "<strong>Degree Path Explorer:</strong><br>" + message;

    chatMessages.appendChild(botMessage);

    chatMessages.scrollTop = chatMessages.scrollHeight;
  }


  // Checks if the user seems unsure
  function isUnsure(message) {

    const answer = message.toLowerCase();

    return (
      answer.includes("not sure") ||
      answer.includes("don't know") ||
      answer.includes("dont know") ||
      answer.includes("unsure") ||
      answer.includes("no idea")
    );
  }


  // Saves an answer to the user's profile
  function saveAnswer(message) {

    if (currentQuestion === 0) {

      userProfile.name = message;

    }

    else if (currentQuestion === 1) {

      userProfile.interests = message;

    }

    else if (currentQuestion === 2) {

      userProfile.strengths = message;

    }

    else if (currentQuestion === 3) {

      userProfile.careerInterest = message;

    }

    else if (currentQuestion === 4) {

      userProfile.majorInterest = message;

    }

    else if (currentQuestion === 5) {

      userProfile.locationPreference = message;

    }

    else if (currentQuestion === 6) {

      userProfile.costImportance = message;

    }
  }


  // Suggests exploration terms; college records come from the database
  // based on the answers the user gave
  function generateRecommendations() {

    // Combine the important answers into one piece of text
    const answers = (
      userProfile.interests + " " +
      userProfile.strengths + " " +
      userProfile.careerInterest + " " +
      userProfile.careerFollowUp + " " +
      userProfile.majorInterest
    ).toLowerCase();

    let recommendations = [];


    // Journalism / writing / media
    if (
      answers.includes("journalism") ||
      answers.includes("writing") ||
      answers.includes("news") ||
      answers.includes("media")
    ) {

      recommendations.push("Journalism");
      recommendations.push("Communications");
      recommendations.push("Digital Media");

    }


    // Sports
    if (
      answers.includes("sports") ||
      answers.includes("athletics")
    ) {

      recommendations.push("Sport Management");
      recommendations.push("Sports Communication");

    }


    // Technology
    if (
      answers.includes("technology") ||
      answers.includes("computer") ||
      answers.includes("coding") ||
      answers.includes("gaming")
    ) {

      recommendations.push("Computer Science");
      recommendations.push("Information Systems");

    }


    // Math / numbers / data
    if (
      answers.includes("math") ||
      answers.includes("numbers") ||
      answers.includes("data")
    ) {

      recommendations.push("Data Science");
      recommendations.push("Mathematics");
      recommendations.push("Finance");

    }


    // Science
    if (
      answers.includes("science")
    ) {

      recommendations.push("Biology");
      recommendations.push("Environmental Science");

    }


    // Business
    if (
      answers.includes("business") ||
      answers.includes("marketing") ||
      answers.includes("finance")
    ) {

      recommendations.push("Business Administration");
      recommendations.push("Marketing");
      recommendations.push("Finance");

    }


    // Creative interests
    if (
      answers.includes("creative") ||
      answers.includes("art") ||
      answers.includes("design")
    ) {

      recommendations.push("Graphic Design");
      recommendations.push("Digital Media");

    }


    // Hands-on interests
    if (
      answers.includes("hands-on") ||
      answers.includes("hands on") ||
      answers.includes("working with my hands")
    ) {

      recommendations.push("Engineering");
      recommendations.push("Technology");

    }


    // Working with people
    if (
      answers.includes("working with people") ||
      answers.includes("helping people")
    ) {

      recommendations.push("Psychology");
      recommendations.push("Social Work");
      recommendations.push("Education");

    }


    if (userProfile.majorInterest && !isUnsure(userProfile.majorInterest)) {
      recommendations.unshift(userProfile.majorInterest);
    }
    // Remove duplicate recommendations
    recommendations = [...new Set(recommendations)].slice(0, 20);


    // If the chatbot could not find a match
    if (recommendations.length === 0) {

      addBotMessage(
        "I don't have enough information yet to suggest specific areas, " +
        "but we can keep exploring your interests."
      );

      return;
    }


    // Build the recommendation message
    let recommendationMessage =
      "Based on what you've told me, here are some areas you may want to explore:<br><br>";


    // Add each recommendation to the message
    recommendations.forEach(function(major) {

      recommendationMessage +=
        "• " + escapeText(major) + "<br>";

    });


    // Reminder that these are exploration options
    recommendationMessage +=
      "<br>These are starting points to explore, not a final recommendation.";


    // Show recommendations
    addBotMessage(recommendationMessage);
    loadDatabaseExamples(recommendations);
  }



  async function loadDatabaseExamples(majors) {
    const root = document.getElementById('guided-chat');
    const box = document.createElement('div');
    box.className = 'bot-message';
    box.textContent = 'Looking up college examples…';
    chatMessages.appendChild(box);
    try {
      const response = await fetch(root.dataset.recommendationsUrl, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRF-Token': root.dataset.csrf},
        body: JSON.stringify({majors})
      });
      const result = await response.json();
      if (!response.ok) throw new Error('Lookup failed');
      box.replaceChildren();
      const paragraph = (text) => {
        const node = document.createElement('p');
        node.textContent = text;
        box.appendChild(node);
      };
      paragraph(result.note);
      if (!result.majors.length) paragraph('No catalog major names matched. Try the Explore programs menu.');
      for (const major of result.majors) {
        const title = document.createElement('h3');
        title.textContent = major.name;
        box.appendChild(title);
        if (!major.programs.length) paragraph('No ranked programs returned for this major.');
        for (const program of major.programs) {
          const value = Number(program.earnings);
          const earnings = program.earnings !== null && Number.isFinite(value) && value >= 0
            ? new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD', maximumFractionDigits: 0}).format(value)
            : 'Not available';
          paragraph(`${program.college} — ${program.major}. Reported median earnings: ${earnings}`);
        }
        const link = document.createElement('a');
        const url = new URL(root.dataset.exploreUrl, window.location.origin);
        url.searchParams.set('cipcode', major.cipcode);
        link.href = url.href;
        link.textContent = 'Explore programs for this major';
        box.appendChild(link);
      }
      if (result.has_more) paragraph('Showing six matching majors. Use Explore programs for the full catalog.');
    } catch (_) {
      box.textContent = 'Database lookup unavailable. Check the connection or reload if your session expired. ';
      const retry = document.createElement('button');
      retry.type = 'button';
      retry.textContent = 'Retry lookup';
      retry.addEventListener('click', () => {box.remove(); loadDatabaseExamples(majors);});
      box.appendChild(retry);
    }
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // Ask the next normal/core question
  function nextQuestion() {

    // User just entered their name
    if (currentQuestion === 1) {

      addBotMessage(
        "Nice to meet you, " +
        escapeText(userProfile.name) +
        "! " +
        questions[0]
      );

      return;
    }


    // Ask remaining core questions
    if (currentQuestion >= 2 && currentQuestion <= 6) {

      addBotMessage(
        questions[currentQuestion - 1]
      );

      return;
    }


    // Questionnaire complete
    if (currentQuestion === 7) {

      addBotMessage(
        "Thanks, " +
        escapeText(userProfile.name) +
        "! I have enough information to start exploring some areas that may match your interests and preferences."
      );


      // Resolve suggested names against the live catalog
      generateRecommendations();


      userInput.disabled = true;
      sendButton.disabled = true;

    }
  }


  // Handles the user's message
  function sendMessage() {

    const message = userInput.value.trim();


    // Don't allow empty messages
    if (currentQuestion >= 7 || message === "" || message.length > 200) {

      return;

    }


    // Create user's message bubble
    const userMessage = document.createElement("div");

    userMessage.classList.add("user-message");

    userMessage.textContent = message;

    chatMessages.appendChild(userMessage);


    // Clear textbox
    userInput.value = "";


    // --------------------------------
    // HANDLE A FOLLOW-UP ANSWER
    // --------------------------------

    if (followUpMode === true) {

      userProfile.careerFollowUp = message;

      followUpMode = false;


      // Move to the major question
      currentQuestion = 4;


      addBotMessage(
        "Thanks! That gives me a better idea of what you might enjoy. " +
        questions[3]
      );


      chatMessages.scrollTop = chatMessages.scrollHeight;

      return;
    }


    // Save normal answer
    saveAnswer(message);


    // --------------------------------
    // CAREER QUESTION DYNAMIC FOLLOW-UP
    // --------------------------------

    if (currentQuestion === 3 && isUnsure(message)) {

      followUpMode = true;


      addBotMessage(
        "No problem! Let's narrow it down a little.<br><br>" +
        "Which type of work sounds most interesting to you?<br><br>" +
        "• Working with technology<br>" +
        "• Working with people<br>" +
        "• Working with numbers or data<br>" +
        "• Creative work<br>" +
        "• Hands-on work<br>" +
        "• I'm still not sure"
      );


      chatMessages.scrollTop = chatMessages.scrollHeight;

      return;
    }


    // Move to next core question
    currentQuestion++;

    nextQuestion();

    chatMessages.scrollTop = chatMessages.scrollHeight;
  }


  // Send when the button is clicked
  sendButton.addEventListener("click", sendMessage);


  // Send when Enter is pressed
  userInput.addEventListener("keydown", function(event) {

    if (event.key === "Enter" && !event.isComposing) {

      event.preventDefault();

      sendMessage();

    }

  });


})();
