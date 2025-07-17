// Recommendations Page JavaScript
class RecommendationsPage {
  constructor() {
    this.api = new APIService();
    this.init();
  }

  init() {
    this.setupEventListeners();
    this.setupBudgetSlider();
    this.setupInterestCheckboxes();
    this.populateCountryDropdown();
    this.setupBookingForm();
  }

  setupEventListeners() {
    const form = document.getElementById("recommendationsForm");
    if (form) {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        this.generateRecommendations();
      });
    }
  }

  setupBudgetSlider() {
    const budgetSlider = document.getElementById("budgetRange");
    const budgetValue = document.getElementById("budgetValue");

    if (budgetSlider && budgetValue) {
      budgetSlider.addEventListener("input", (e) => {
        const value = parseInt(e.target.value);
        budgetValue.textContent = `$${value.toLocaleString()}`;
      });
    }
  }

  setupInterestCheckboxes() {
    const checkboxes = document.querySelectorAll(
      '.interest-checkbox input[type="checkbox"]'
    );
    checkboxes.forEach((checkbox) => {
      checkbox.addEventListener("change", (e) => {
        const label = e.target.closest(".interest-checkbox");
        if (e.target.checked) {
          label.classList.add("checked");
        } else {
          label.classList.remove("checked");
        }
      });
    });
  }

  async populateCountryDropdown() {
    const countrySelect = document.getElementById("countrySelect");
    if (!countrySelect) return;
    // Use APIService fallback for now (could be replaced with backend call)
    const continents = await this.api.getContinents();
    console.log("populateCountryDropdown: continents =", continents);
    console.log("populateCountryDropdown: continents.data =", continents.data);
    let countries = [];
    let dataArr = [];
    if (Array.isArray(continents.data)) {
      dataArr = continents.data;
    } else if (continents.data && Array.isArray(continents.data.data)) {
      dataArr = continents.data.data;
    } else {
      console.error(
        "populateCountryDropdown: continents.data is not an array",
        continents.data
      );
      countrySelect.innerHTML =
        '<option value="">No countries found (continent data error)</option>';
      return;
    }
    for (const cont of dataArr) {
      const countryResp = await this.api.getCountriesByContinent(cont.name);
      if (countryResp.success && countryResp.data) {
        countries = countries.concat(countryResp.data.map((c) => c.name));
      }
    }
    countries = [...new Set(countries)].sort();
    countrySelect.innerHTML =
      '<option value="">Select country</option>' +
      countries.map((c) => `<option value="${c}">${c}</option>`).join("");
  }

  getFormData() {
    const ageGroup = document.getElementById("ageGroup").value;
    const groupSize = document.getElementById("groupSize").value;
    const country = document.getElementById("countrySelect").value;
    const budgetRange = document.getElementById("budgetRange").value;
    const tripDuration = document.getElementById("tripDuration").value;
    const additionalNotes = document.getElementById("additionalNotes").value;

    // Get selected interests
    const selectedInterests = [];
    const interestCheckboxes = document.querySelectorAll(
      '.interest-checkbox input[type="checkbox"]:checked'
    );
    interestCheckboxes.forEach((checkbox) => {
      selectedInterests.push(checkbox.value);
    });

    return {
      ageGroup,
      groupSize,
      country,
      budgetRange: parseInt(budgetRange),
      tripDuration,
      interests: selectedInterests,
      additionalNotes,
    };
  }

  validateForm() {
    const data = this.getFormData();

    if (!data.ageGroup) {
      uiComponents.showToast("Please select your age group", "error");
      return false;
    }

    if (!data.groupSize) {
      uiComponents.showToast("Please select your group size", "error");
      return false;
    }

    if (!data.country) {
      uiComponents.showToast("Please select your country", "error");
      return false;
    }

    if (!data.tripDuration) {
      uiComponents.showToast("Please select your trip duration", "error");
      return false;
    }

    if (data.interests.length === 0) {
      uiComponents.showToast("Please select at least one interest", "error");
      return false;
    }

    return true;
  }

  async generateRecommendations() {
    if (!this.validateForm()) {
      return;
    }

    const formData = this.getFormData();

    // Show loading state
    this.showLoadingState();

    try {
      const response = await this.api.generatePersonalizedRecommendations(
        formData
      );

      if (response.success) {
        this.displayRecommendations(response.data);
      } else {
        throw new Error(
          response.message || "Failed to generate recommendations"
        );
      }
    } catch (error) {
      console.error("Recommendations generation failed:", error);
      uiComponents.showToast(
        `Failed to generate recommendations: ${error.message}`,
        "error"
      );
    } finally {
      this.hideLoadingState();
    }
  }

  showLoadingState() {
    const form = document.querySelector(".preferences-form");
    const loadingState = document.getElementById("loadingState");
    const results = document.getElementById("recommendationsResults");

    if (form) form.style.display = "none";
    if (loadingState) loadingState.style.display = "block";
    if (results) results.style.display = "none";
  }

  hideLoadingState() {
    const form = document.querySelector(".preferences-form");
    const loadingState = document.getElementById("loadingState");

    if (form) form.style.display = "block";
    if (loadingState) loadingState.style.display = "none";
  }

  async handleFormSubmit(e) {
    e.preventDefault();
    // Gather form data
    const formData = this.getFormData();
    // Show loading state
    this.showLoadingRecommendations();
    try {
      // Fetch real recommendations from backend (OpenAI-powered)
      const response = await this.api.getRecommendations(formData);
      if (
        response &&
        response.success &&
        response.data &&
        response.data.destinations
      ) {
        this.displayRecommendations(response.data);
      } else {
        this.showError("No recommendations found.");
      }
    } catch (error) {
      this.showError("Failed to fetch recommendations.");
    } finally {
      this.hideLoadingRecommendations();
    }
  }

  displayRecommendations(data) {
    console.log("Displaying recommendations:", data);

    const results = document.getElementById("recommendationsResults");
    const content = document.getElementById("recommendationsContent");
    if (!results || !content) {
      console.error("Recommendations results or content elements not found");
      return;
    }

    let html = "";
    // Display destinations as clickable cards
    if (data.destinations && data.destinations.length > 0) {
      console.log(`Creating ${data.destinations.length} destination cards`);

      html += '<div class="recommendation-card">';
      html += data.destinations
        .map(
          (dest) => `
        <div class="destination-card" data-dest-id="${
          dest.id || "unknown"
        }" style="cursor: pointer;">
          <img src="${dest.image_url || ""}" alt="${dest.name}" />
          <h3>${dest.name}</h3>
          <p>${dest.description || ""}</p>
        </div>
      `
        )
        .join("");
      html += "</div>";
    } else {
      html = "<p>No destinations found.</p>";
    }

    content.innerHTML = html;
    results.style.display = "block";

    // Add click handlers to destination cards
    const cards = content.querySelectorAll(".destination-card");
    console.log(
      `Found ${cards.length} destination cards to attach click handlers`
    );

    cards.forEach((card, index) => {
      card.addEventListener("click", (e) => {
        console.log(`Destination card ${index} clicked`);

        // Use the index to find the destination instead of relying on ID
        if (index < data.destinations.length) {
          const dest = data.destinations[index];
          console.log(
            "Destination found by index, calling handleDestinationSelect:",
            dest
          );
          this.handleDestinationSelect(dest);
        } else {
          console.error(
            "Destination index out of bounds:",
            index,
            "total destinations:",
            data.destinations.length
          );
        }
      });
    });
  }

  handleDestinationSelect(dest) {
    console.log("Destination selected:", dest);

    // Hide recommendations
    const recommendationsResults = document.getElementById(
      "recommendationsResults"
    );
    if (recommendationsResults) {
      recommendationsResults.style.display = "none";
    }

    // Store selected destination for booking
    this.selectedDestination = dest;

    // Generate detailed itinerary first
    this.generateDetailedItinerary(dest);
  }

  async generateDetailedItinerary(dest) {
    console.log("Generating detailed itinerary for:", dest);

    const content = document.getElementById("recommendationsContent");
    if (!content) return;

    // Show loading state
    content.innerHTML = `
      <div class="loading-state">
        <div class="loading-spinner"></div>
        <div class="loading-text">Generating detailed itinerary...</div>
        <div class="loading-subtext">Creating your perfect trip plan</div>
      </div>
    `;

    try {
      // Get user preferences for personalized itinerary
      const userPrefs = this.getFormData();

      const response = await fetch(
        "http://localhost:8000/api/generate-detailed-itinerary",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            destination: dest.name,
            duration: userPrefs.tripDuration,
            budget_level: this.getBudgetLevel(userPrefs.budgetRange),
            travelers: parseInt(userPrefs.groupSize) || 2,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.success && data.data) {
        this.displayDetailedItinerary(data.data, dest);
      } else {
        throw new Error("Failed to generate itinerary");
      }
    } catch (error) {
      console.error("Error generating itinerary:", error);
      // Fallback to booking form
      this.showBookingForm(dest.name);
    }
  }

  getBudgetLevel(budgetRange) {
    if (budgetRange <= 1000) return "budget";
    if (budgetRange <= 3000) return "mid-range";
    return "luxury";
  }

  displayDetailedItinerary(itineraryData, dest) {
    console.log("Displaying detailed itinerary:", itineraryData);

    // Show the recommendations results section again
    const recommendationsResults = document.getElementById(
      "recommendationsResults"
    );
    if (recommendationsResults) {
      recommendationsResults.style.display = "block";
    }

    const content = document.getElementById("recommendationsContent");
    if (!content) return;

    let html = `
      <div class="detailed-itinerary">
        <!-- Trip Overview -->
        <div class="trip-overview">
          <h3>${
            itineraryData.tripOverview?.title || `${dest.name} Adventure`
          }</h3>
          <div class="trip-meta">
            <span>📍 ${
              itineraryData.tripOverview?.destination || dest.name
            }</span>
            <span>⏰ ${itineraryData.tripOverview?.duration || "7 days"}</span>
            <span>👥 ${
              itineraryData.tripOverview?.travelers || 2
            } travelers</span>
            <span>🌤️ Best: ${
              itineraryData.tripOverview?.bestTime || "Year-round"
            }</span>
          </div>
          <p class="trip-summary">${
            itineraryData.tripOverview?.summary ||
            "An amazing adventure awaits!"
          }</p>
        </div>

        <!-- Daily Itinerary -->
        <div class="daily-itinerary">
          <h4>📅 Day-by-Day Plan</h4>
          ${this.generateDailyItineraryHTML(itineraryData.dailyItinerary)}
        </div>

        <!-- Budget Breakdown -->
        <div class="budget-section">
          <h4>💰 Budget Breakdown</h4>
          ${this.generateBudgetHTML(itineraryData.budgetBreakdown)}
        </div>

        <!-- Travel Tips -->
        <div class="tips-section">
          <h4>💡 Travel Tips</h4>
          ${this.generateTipsHTML(itineraryData.travelTips)}
        </div>

        <!-- Accommodations -->
        <div class="accommodations-section">
          <h4>🏨 Recommended Accommodations</h4>
          ${this.generateAccommodationsHTML(itineraryData.accommodations)}
        </div>

        <!-- Restaurants -->
        <div class="restaurants-section">
          <h4>🍽️ Restaurant Recommendations</h4>
          ${this.generateRestaurantsHTML(itineraryData.restaurants)}
        </div>

        <!-- Book This Trip Button -->
        <div class="booking-action">
          <button class="btn btn-primary btn-large" id="book-this-trip">
            <i class="fas fa-plane"></i>
            Book This Trip
          </button>
        </div>
      </div>
    `;

    content.innerHTML = html;

    // Add click handler for booking button
    const bookButton = document.getElementById("book-this-trip");
    if (bookButton) {
      bookButton.onclick = () => {
        this.showBookingForm(dest.name);
      };
    }
  }

  generateDailyItineraryHTML(days) {
    if (!days || !Array.isArray(days))
      return "<p>Daily itinerary not available</p>";

    return days
      .map(
        (day) => `
      <div class="day-card">
        <h5>Day ${day.day}: ${day.title}</h5>
        <div class="timeline">
          ${
            day.morning
              ? `<div class="time-slot morning">
            <span class="time">🌅 Morning</span>
            <ul>${day.morning
              .map((activity) => `<li>${activity}</li>`)
              .join("")}</ul>
          </div>`
              : ""
          }
          ${
            day.afternoon
              ? `<div class="time-slot afternoon">
            <span class="time">☀️ Afternoon</span>
            <ul>${day.afternoon
              .map((activity) => `<li>${activity}</li>`)
              .join("")}</ul>
          </div>`
              : ""
          }
          ${
            day.evening
              ? `<div class="time-slot evening">
            <span class="time">🌙 Evening</span>
            <ul>${day.evening
              .map((activity) => `<li>${activity}</li>`)
              .join("")}</ul>
          </div>`
              : ""
          }
        </div>
        <div class="day-details">
          <span class="accommodation">🏨 ${day.accommodation || "Hotel"}</span>
          <span class="meals">🍽️ ${
            day.meals?.join(", ") || "Meals included"
          }</span>
          <span class="transport">🚗 ${
            day.transportation || "Transport provided"
          }</span>
        </div>
      </div>
    `
      )
      .join("");
  }

  generateBudgetHTML(budget) {
    if (!budget) return "<p>Budget information not available</p>";

    return `
      <div class="budget-breakdown">
        <div class="budget-item">
          <span class="budget-category">🏨 Accommodation</span>
          <span class="budget-amount">$${
            budget.accommodation?.total || 0
          }</span>
        </div>
        <div class="budget-item">
          <span class="budget-category">🍽️ Meals</span>
          <span class="budget-amount">$${budget.meals?.total || 0}</span>
        </div>
        <div class="budget-item">
          <span class="budget-category">🎯 Activities</span>
          <span class="budget-amount">$${budget.activities?.total || 0}</span>
        </div>
        <div class="budget-item">
          <span class="budget-category">🚗 Transportation</span>
          <span class="budget-amount">$${
            budget.transportation?.total || 0
          }</span>
        </div>
        <div class="budget-item">
          <span class="budget-category">💡 Miscellaneous</span>
          <span class="budget-amount">$${
            budget.miscellaneous?.total || 0
          }</span>
        </div>
        <div class="budget-total">
          <span class="budget-category">💰 Total Trip Cost</span>
          <span class="budget-amount">$${budget.totalTripCost || 0}</span>
        </div>
        <div class="budget-per-person">
          <span class="budget-category">👤 Cost per Person</span>
          <span class="budget-amount">$${budget.costPerPerson || 0}</span>
        </div>
      </div>
    `;
  }

  generateTipsHTML(tips) {
    if (!tips || !Array.isArray(tips))
      return "<p>Travel tips not available</p>";

    return tips
      .map(
        (category) => `
      <div class="tips-category">
        <h5>${category.category}</h5>
        <ul>
          ${category.tips.map((tip) => `<li>${tip}</li>`).join("")}
        </ul>
      </div>
    `
      )
      .join("");
  }

  generateAccommodationsHTML(accommodations) {
    if (!accommodations || !Array.isArray(accommodations))
      return "<p>Accommodation recommendations not available</p>";

    return accommodations
      .map(
        (hotel) => `
      <div class="accommodation-item">
        <h5>${hotel.name}</h5>
        <div class="meta">
          <span>${hotel.type}</span>
          <span>📍 ${hotel.location}</span>
          <span>💰 ${hotel.price}</span>
          <span>⭐ ${hotel.rating}</span>
        </div>
        <div class="amenities">
          <h6>Amenities</h6>
          <ul>
            ${
              hotel.amenities
                ?.map((amenity) => `<li>${amenity}</li>`)
                .join("") || "<li>Standard amenities included</li>"
            }
          </ul>
        </div>
        ${
          hotel.pros && hotel.cons
            ? `
        <div class="pros-cons">
          <div class="pros">
            <h6>Pros</h6>
            <ul>
              ${hotel.pros.map((pro) => `<li>${pro}</li>`).join("")}
            </ul>
          </div>
          <div class="cons">
            <h6>Cons</h6>
            <ul>
              ${hotel.cons.map((con) => `<li>${con}</li>`).join("")}
            </ul>
          </div>
        </div>
        `
            : ""
        }
      </div>
    `
      )
      .join("");
  }

  generateRestaurantsHTML(restaurants) {
    if (!restaurants || !Array.isArray(restaurants))
      return "<p>Restaurant recommendations not available</p>";

    return restaurants
      .map(
        (restaurant) => `
      <div class="restaurant-item">
        <h5>${restaurant.name}</h5>
        <div class="meta">
          <span>${restaurant.cuisine}</span>
          <span>${restaurant.priceRange}</span>
          <span>⭐ ${restaurant.rating}</span>
          <span>📍 ${restaurant.location}</span>
        </div>
        <div class="dishes">
          <h6>Best Dishes</h6>
          <ul>
            ${
              restaurant.bestDishes
                ?.map((dish) => `<li>${dish}</li>`)
                .join("") || `<li>${restaurant.specialty}</li>`
            }
          </ul>
        </div>
        ${
          restaurant.reservationRequired !== undefined
            ? `
        <div class="reservation">
          <span class="reservation-status">
            ${
              restaurant.reservationRequired
                ? "📞 Reservation Required"
                : "✅ Walk-ins Welcome"
            }
          </span>
        </div>
        `
            : ""
        }
      </div>
    `
      )
      .join("");
  }

  showBookingForm(destName) {
    console.log("Showing booking form for destination:", destName);

    // Show booking section, pre-fill destination
    const bookingSection = document.getElementById("spa-booking-section");
    if (!bookingSection) {
      console.error("Booking section not found");
      return;
    }

    bookingSection.style.display = "block";

    // Pre-fill destination with airport code if possible
    const flightToInput = document.getElementById("flight-to");
    if (flightToInput) {
      // Try to extract airport code from destination name
      // For now, use a simple mapping or just use the name
      // You can enhance this with a proper airport code lookup
      flightToInput.value = destName;
    }

    // Optionally scroll to booking form
    bookingSection.scrollIntoView({ behavior: "smooth" });

    // Ensure booking form is properly initialized
    this.setupBookingForm();

    // Force re-initialization of autocomplete and date pickers
    this.initializeAutocomplete();
    this.initializeDatePickers();
  }

  async handleBookingSearch() {
    // Get booking form data
    const from = document.getElementById("flight-from").value;
    const to = document.getElementById("flight-to").value;
    const depart = document.getElementById("flight-depart").value;
    const ret = document.getElementById("flight-return").value;
    const passengers = document.getElementById("flight-passengers").value;
    const classType = document.getElementById("flight-class").value;
    // Basic validation
    if (!from || !to || !depart) {
      uiComponents.showToast(
        "Please fill in all required booking fields",
        "error"
      );
      return;
    }
    // Call backend flight search
    const params = {
      from_location: from,
      to_location: to,
      departure_date: depart,
      return_date: ret,
      passengers: parseInt(passengers),
      class_type: classType,
      search_type: "flights",
    };
    // Show loading in results
    const resultsDiv = document.getElementById("spa-flight-results");
    const grid = document.getElementById("spa-flight-results-grid");
    resultsDiv.style.display = "block";
    grid.innerHTML =
      '<div style="text-align:center;padding:30px;">Searching for flights...</div>';
    try {
      const resp = await fetch("http://localhost:8000/api/search-bookings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
      });
      const data = await resp.json();
      if (data.results && data.results.length > 0) {
        grid.innerHTML = data.results
          .map(
            (flight, idx) => `
          <div class="flight-result-card" style="background:#f8f9fa;padding:15px;margin-bottom:10px;border-radius:8px;">
            <div><b>${flight.airline}</b> ${flight.flightNumber} (${flight.class})</div>
            <div>${flight.from} → ${flight.to}</div>
            <div>Departure: ${flight.departureDate} ${flight.departureTime}</div>
            <div>Duration: ${flight.duration}</div>
            <div>Stops: ${flight.stops}</div>
            <div>Price: <b>$${flight.price}</b></div>
            <button class="btn btn-success spa-book-confirm-btn" data-idx="${idx}" style="margin-top:10px;">Book Now</button>
                        </div>
        `
          )
          .join("");
        // Add confirmation logic
        document.querySelectorAll(".spa-book-confirm-btn").forEach((btn) => {
          btn.onclick = (e) => {
            const idx = btn.getAttribute("data-idx");
            this.showBookingConfirmation(data.results[idx]);
          };
        });
      } else {
        grid.innerHTML =
          '<div style="text-align:center;padding:30px;">No flights found.</div>';
      }
    } catch (err) {
      grid.innerHTML =
        '<div style="text-align:center;padding:30px;color:red;">Error searching for flights.</div>';
    }
  }

  showBookingConfirmation(flight) {
    const grid = document.getElementById("spa-flight-results-grid");
    grid.innerHTML = `<div class="booking-confirmation" style="background:#e8f5e8;padding:30px;border-radius:10px;text-align:center;">
      <h3 style="color:#27ae60;"><i class="fas fa-check-circle"></i> Booking Confirmed!</h3>
      <p>Your flight booking is confirmed:</p>
      <div style="margin:20px 0;">
        <b>${flight.airline}</b> ${flight.flightNumber} (${flight.class})<br/>
        ${flight.from} → ${flight.to}<br/>
        Departure: ${flight.departureDate} ${flight.departureTime}<br/>
        Price: <b>$${flight.price}</b>
                    </div>
      <p>Check your email for the ticket and details. Have a great trip!</p>
    </div>`;
  }

  setupBookingForm() {
    console.log("Setting up booking form...");

    // Initialize date pickers
    this.initializeDatePickers();

    // Initialize autocomplete for destination inputs
    this.initializeAutocomplete();

    // Attach search handler
    const searchBtn = document.getElementById("spa-search-flights");
    if (searchBtn) {
      searchBtn.onclick = (e) => {
        e.preventDefault();
        this.performFlightSearch();
      };
    }
  }

  initializeDatePickers() {
    console.log("Initializing date pickers...");

    if (typeof flatpickr !== "undefined") {
      ["flight-depart", "flight-return"].forEach((id) => {
        const input = document.getElementById(id);
        if (input) {
          console.log(`Initializing date picker for ${id}`);

          // Destroy existing instance if any
          if (input._flatpickr) {
            input._flatpickr.destroy();
          }

          flatpickr(input, {
            dateFormat: "Y-m-d",
            minDate: "today",
            disableMobile: true,
            allowInput: false,
            clickOpens: true,
            wrap: false,
            onChange: function (selectedDates, dateStr, instance) {
              console.log(`Date selected for ${id}: ${dateStr}`);
            },
          });
        } else {
          console.warn(`Date picker input not found: ${id}`);
        }
      });
    } else {
      console.warn("Flatpickr not loaded, date pickers will not work");
    }
  }

  initializeAutocomplete() {
    console.log("Initializing autocomplete...");

    const destinationInputs = ["flight-from", "flight-to"];

    destinationInputs.forEach((inputId) => {
      const input = document.getElementById(inputId);
      if (!input) {
        console.warn(`Autocomplete input not found: ${inputId}`);
        return;
      }

      console.log(`Setting up autocomplete for ${inputId}`);

      let suggestionsContainer = null;
      let debounceTimer = null;

      // Remove existing event listeners by cloning the element
      const newInput = input.cloneNode(true);
      input.parentNode.replaceChild(newInput, input);
      const freshInput = document.getElementById(inputId);

      freshInput.addEventListener("input", (e) => {
        const query = e.target.value ? e.target.value.trim() : "";
        console.log(`Autocomplete input for ${inputId}: "${query}"`);

        // Remove existing suggestions
        if (suggestionsContainer) {
          suggestionsContainer.remove();
          suggestionsContainer = null;
        }

        if (query.length < 2) return;

        // Create suggestions container
        suggestionsContainer = document.createElement("div");
        suggestionsContainer.className = "autocomplete-suggestions";
        suggestionsContainer.style.cssText = `
          position: absolute;
          top: 100%;
          left: 0;
          right: 0;
          background: white;
          border: 1px solid #ddd;
          border-top: none;
          max-height: 200px;
          overflow-y: auto;
          z-index: 1000;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        `;

        freshInput.parentNode.style.position = "relative";
        freshInput.parentNode.appendChild(suggestionsContainer);

        // Debounce the API call
        debounceTimer = setTimeout(() => {
          try {
            // For flight search, show airport codes
            if (
              freshInput.id === "flight-from" ||
              freshInput.id === "flight-to"
            ) {
              const airportSuggestions = this.getAirportSuggestions(query);
              console.log(
                `Found ${airportSuggestions.length} airport suggestions for "${query}"`
              );
              if (airportSuggestions.length > 0) {
                this.showSuggestions(freshInput, airportSuggestions);
              }
            }
          } catch (error) {
            console.error("Autocomplete error:", error);
          }
        }, 300);
      });

      // Hide suggestions when clicking outside
      document.addEventListener("click", (e) => {
        if (
          suggestionsContainer &&
          !freshInput.contains(e.target) &&
          !suggestionsContainer.contains(e.target)
        ) {
          suggestionsContainer.remove();
          suggestionsContainer = null;
        }
      });
    });
  }

  getAirportSuggestions(query) {
    // Use the shared airports array from airports.js
    return airports.filter(
      (airport) =>
        airport.code.toLowerCase().includes(query.toLowerCase()) ||
        airport.name.toLowerCase().includes(query.toLowerCase()) ||
        (airport.full &&
          airport.full.toLowerCase().includes(query.toLowerCase()))
    );
  }

  showSuggestions(input, suggestions) {
    const container = input.parentNode.querySelector(
      ".autocomplete-suggestions"
    );
    if (!container) return;

    container.innerHTML = suggestions
      .map(
        (suggestion) => `
        <div class="suggestion-item" style="padding: 10px; cursor: pointer; border-bottom: 1px solid #eee;">
          <div style="font-weight: bold;">${suggestion.code}</div>
          <div style="font-size: 0.9em; color: #666;">${suggestion.name}</div>
        </div>
      `
      )
      .join("");

    // Add click handlers
    container.querySelectorAll(".suggestion-item").forEach((item, index) => {
      item.addEventListener("click", () => {
        input.value = suggestions[index].full;
        container.remove();
      });
    });
  }

  async performFlightSearch() {
    const searchButton = document.getElementById("spa-search-flights");
    const resultsGrid = document.getElementById("spa-flight-results-grid");

    if (searchButton) {
      searchButton.disabled = true;
      searchButton.innerHTML =
        '<i class="fas fa-spinner fa-spin"></i> Searching...';
    }

    if (resultsGrid) {
      resultsGrid.innerHTML = `
        <div class="loading-state">
          <div class="loading-spinner"></div>
          <div class="loading-text">Searching for flights...</div>
          <div class="loading-subtext">This may take a few moments</div>
        </div>
      `;
    }

    try {
      // Use the Amadeus flight search endpoint
      const searchData = this.getFlightSearchData();
      console.log("Flight search data:", searchData);

      const response = await fetch("http://localhost:8000/api/search-flights", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(searchData),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log("Flight search response:", data);

      if (data.success && data.flights && data.flights.length > 0) {
        console.log(
          `Found ${data.flights.length} flights from ${data.provider || "API"}`
        );
        this.displayFlightResults(data.flights);
        this.showToast(
          `Found ${data.flights.length} flight options! (${
            data.provider || "API"
          })`,
          "success"
        );
      } else {
        console.log("No flights found in API response, using mock data");
        // Fallback to mock data if no results
        const mockResults = this.getMockFlightResults();
        this.displayFlightResults(mockResults);
        this.showToast(
          `Found ${mockResults.length} flight options! (mock data)`,
          "success"
        );
      }
    } catch (error) {
      console.error("Search error:", error);
      this.showToast("Search failed. Using mock data...", "warning");

      // Fallback to mock data
      const mockResults = this.getMockFlightResults();
      this.displayFlightResults(mockResults);
    } finally {
      if (searchButton) {
        searchButton.disabled = false;
        searchButton.innerHTML = '<i class="fas fa-search"></i> Search Flights';
      }
    }
  }

  getFlightSearchData() {
    // Get raw input values
    const originInput = document.getElementById("flight-from")?.value || "";
    const destinationInput = document.getElementById("flight-to")?.value || "";

    // Extract airport codes (handle formats like "JFK - New York" -> "JFK")
    let origin = originInput.toUpperCase();
    let destination = destinationInput.toUpperCase();

    // Extract 3-letter airport codes from the beginning of the string
    if (origin.includes(" - ")) {
      origin = origin.split(" - ")[0].trim();
    }
    if (destination.includes(" - ")) {
      destination = destination.split(" - ")[0].trim();
    }

    // Additional cleanup - remove any extra text after the 3-letter code
    origin = origin.substring(0, 3);
    destination = destination.substring(0, 3);

    console.log(`Extracted airport codes: ${origin} -> ${destination}`);

    const data = {
      origin: origin,
      destination: destination,
      departure_date: document.getElementById("flight-depart")?.value || "",
      return_date: document.getElementById("flight-return")?.value || null,
      adults: parseInt(
        document.getElementById("flight-passengers")?.value || 1
      ),
      children: 0,
      infants: 0,
      travel_class:
        document.getElementById("flight-class")?.value?.toUpperCase() ||
        "ECONOMY",
      currency_code: "USD",
    };

    // Convert travel class to Amadeus format
    const classMap = {
      economy: "ECONOMY",
      premium: "PREMIUM_ECONOMY",
      business: "BUSINESS",
      first: "FIRST",
    };

    if (classMap[data.travel_class.toLowerCase()]) {
      data.travel_class = classMap[data.travel_class.toLowerCase()];
    }

    return data;
  }

  getMockFlightResults() {
    return [
      {
        id: "mock_flight_1",
        itineraries: [
          {
            segments: [
              {
                departure: { iataCode: "JFK", at: "2024-06-15T10:00:00" },
                arrival: { iataCode: "LAX", at: "2024-06-15T13:30:00" },
                carrierCode: "AA",
                number: "123",
                aircraft: { code: "B737" },
              },
            ],
          },
        ],
        price: { total: "299.99", currency: "USD" },
        travelerPricings: [{ fareDetailsBySegment: [{ cabin: "ECONOMY" }] }],
      },
      {
        id: "mock_flight_2",
        itineraries: [
          {
            segments: [
              {
                departure: { iataCode: "JFK", at: "2024-06-15T14:00:00" },
                arrival: { iataCode: "LAX", at: "2024-06-15T17:30:00" },
                carrierCode: "DL",
                number: "456",
                aircraft: { code: "A320" },
              },
            ],
          },
        ],
        price: { total: "349.99", currency: "USD" },
        travelerPricings: [{ fareDetailsBySegment: [{ cabin: "ECONOMY" }] }],
      },
    ];
  }

  displayFlightResults(flights) {
    console.log(`Displaying ${flights.length} flight results`);

    const resultsGrid = document.getElementById("spa-flight-results-grid");
    if (!resultsGrid) {
      console.error("Flight results grid not found");
      return;
    }

    if (flights.length === 0) {
      resultsGrid.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon"><i class="fas fa-search"></i></div>
          <div class="empty-title">No flights found</div>
          <div class="empty-description">Try adjusting your search criteria.</div>
        </div>
      `;
      return;
    }

    const flightCards = flights.map((flight) => this.createFlightCard(flight));
    resultsGrid.innerHTML = flightCards.join("");

    // Add booking event listeners
    this.addBookingEventListeners();
  }

  createFlightCard(flight) {
    console.log("Flight card data:", flight);

    // Handle both Amadeus API and mock data formats
    let from,
      to,
      airline,
      flightNumber,
      aircraft,
      departureTime,
      departureDate,
      duration,
      price,
      currency,
      stops,
      classType,
      flightId;

    if (flight.itineraries && flight.itineraries.length > 0) {
      // Amadeus API format
      const itinerary = flight.itineraries[0];
      const segment = itinerary.segments[0];

      from = segment.departure.iataCode || "Unknown";
      to = segment.arrival.iataCode || "Unknown";
      airline = segment.carrierCode || "Unknown Airline";
      flightNumber = `${segment.carrierCode}${segment.number}` || "XX1234";
      aircraft = segment.aircraft?.code || "Boeing 737";
      departureTime = segment.departure.at
        ? new Date(segment.departure.at).toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
          })
        : "12:00 PM";
      departureDate = segment.departure.at
        ? new Date(segment.departure.at).toLocaleDateString()
        : "2024-06-15";

      // Calculate duration
      if (segment.departure.at && segment.arrival.at) {
        const depTime = new Date(segment.departure.at);
        const arrTime = new Date(segment.arrival.at);
        const diffMs = arrTime - depTime;
        const hours = Math.floor(diffMs / (1000 * 60 * 60));
        const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
        duration = `${hours}h ${minutes}m`;
      } else {
        duration = "3h 30m";
      }

      price = flight.price?.total ? parseFloat(flight.price.total) : 299;
      currency = flight.price?.currency || "USD";
      stops = itinerary.segments.length - 1;
      classType =
        flight.travelerPricings?.[0]?.fareDetailsBySegment?.[0]?.cabin ||
        "Economy";
      flightId =
        flight.id ||
        `flight_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    } else {
      // Mock data format (fallback)
      from = flight.from || "JFK";
      to = flight.to || "LAX";
      airline = flight.airline || "Sample Airlines";
      flightNumber = flight.flightNumber || "XX1234";
      aircraft = flight.aircraft || "Boeing 737";
      departureTime = flight.departureTime || "10:00 AM";
      departureDate = flight.departureDate || "2024-06-15";
      duration = flight.duration || "3h 30m";
      price = flight.price || 299;
      currency = "USD";
      stops = flight.stops || 0;
      classType = flight.class || "Economy";
      flightId =
        flight.id ||
        `flight_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    return `
      <div class="flight-card">
        <div class="flight-route">
          <div class="flight-route-info">
            <div class="flight-cities">${from} → ${to}</div>
            <div class="flight-airlines">${airline}</div>
            <div class="flight-details">Flight ${flightNumber} • ${aircraft} • ${stops} stop${
      stops !== 1 ? "s" : ""
    }</div>
          </div>
        </div>
        <div class="flight-times">
          <div class="flight-time">${departureTime}</div>
          <div class="flight-date">${departureDate}</div>
        </div>
        <div class="flight-duration">${duration}</div>
        <div class="flight-price">
          <div class="price-amount">
            <div class="primary-price">${this.getCurrencySymbol(
              currency
            )}${price}</div>
            ${
              currency !== "USD"
                ? `<div class="secondary-price">$${(
                    price * this.getExchangeRate(currency, "USD")
                  ).toFixed(0)}</div>`
                : ""
            }
            ${
              currency !== "INR"
                ? `<div class="secondary-price">₹${(
                    price * this.getExchangeRate(currency, "INR")
                  ).toFixed(0)}</div>`
                : ""
            }
          </div>
          <div class="price-per">per person</div>
          <div class="price-class">${classType}</div>
        </div>
        <div class="flight-actions">
          <button class="btn btn-primary btn-small" onclick="recommendationsPage.handleBooking('flights', '${flightId}')">
            <i class="fas fa-plane"></i>
            Book Flight
          </button>
        </div>
      </div>
    `;
  }

  getCurrencySymbol(currency) {
    const symbols = {
      USD: "$",
      EUR: "€",
      GBP: "£",
      INR: "₹",
      JPY: "¥",
    };
    return symbols[currency] || "$";
  }

  getExchangeRate(from, to) {
    // Mock exchange rates
    const rates = {
      USD: { EUR: 0.85, GBP: 0.73, INR: 75, JPY: 110 },
      EUR: { USD: 1.18, GBP: 0.86, INR: 88, JPY: 129 },
      GBP: { USD: 1.37, EUR: 1.16, INR: 102, JPY: 150 },
      INR: { USD: 0.013, EUR: 0.011, GBP: 0.0098, JPY: 1.47 },
      JPY: { USD: 0.0091, EUR: 0.0077, GBP: 0.0067, INR: 0.68 },
    };
    return rates[from]?.[to] || 1;
  }

  addBookingEventListeners() {
    // This will be handled by the onclick in createFlightCard
  }

  async handleBooking(type, id) {
    console.log(`Booking ${type} with id: ${id}`);

    // Show booking modal
    this.showBookingModal(type, id);
  }

  showBookingModal(type, id) {
    // Create and show booking modal
    const modal = document.createElement("div");
    modal.className = "modal";
    modal.innerHTML = `
      <div class="modal-content">
        <div class="modal-header">
          <h3>Complete Your Booking</h3>
          <span class="close">&times;</span>
        </div>
        <div class="modal-body">
          <form id="booking-form">
            <div class="form-group">
              <label for="customer-name">Full Name *</label>
              <input type="text" id="customer-name" required>
            </div>
            <div class="form-group">
              <label for="customer-email">Email *</label>
              <input type="email" id="customer-email" required>
            </div>
            <div class="form-group">
              <label for="customer-phone">Phone</label>
              <input type="tel" id="customer-phone">
            </div>
            <div class="form-group">
              <label for="travel-date">Travel Date *</label>
              <input type="date" id="travel-date" required>
            </div>
            <div class="form-group">
              <label for="passengers">Passengers</label>
              <select id="passengers">
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="4">4</option>
              </select>
            </div>
            <div class="form-group">
              <label for="special-requests">Special Requests</label>
              <textarea id="special-requests"></textarea>
            </div>
            <button type="submit" class="btn btn-primary">Confirm Booking</button>
          </form>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Close modal functionality
    const closeBtn = modal.querySelector(".close");
    closeBtn.onclick = () => modal.remove();

    // Handle form submission
    const form = modal.querySelector("#booking-form");
    form.onsubmit = async (e) => {
      e.preventDefault();
      await this.submitBooking(type, id, form, modal);
    };
  }

  async submitBooking(type, id, form, modal) {
    const submitButton = form.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;

    try {
      submitButton.textContent = "Processing...";
      submitButton.disabled = true;

      const formData = {
        booking_type: type,
        item_id: id,
        customer_name: form.querySelector("#customer-name").value.trim(),
        customer_email: form.querySelector("#customer-email").value.trim(),
        customer_phone:
          form.querySelector("#customer-phone").value.trim() || null,
        travel_date: form.querySelector("#travel-date").value,
        return_date: null,
        passengers: parseInt(form.querySelector("#passengers").value),
        special_requests:
          form.querySelector("#special-requests").value.trim() || null,
        total_price: 299.99, // Mock price
        currency: "USD",
      };

      const response = await fetch("http://localhost:8000/api/book", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || "Booking failed. Please try again."
        );
      }

      const result = await response.json();
      this.showToast("Booking confirmed successfully!", "success");
      modal.remove();

      // Show success page
      this.showBookingSuccess();
    } catch (error) {
      console.error("Booking error:", error);
      this.showToast(
        error.message || "Booking failed. Please try again.",
        "error"
      );
    } finally {
      submitButton.textContent = originalText;
      submitButton.disabled = false;
    }
  }

  showBookingSuccess() {
    // Redirect to booking success page
    window.location.href = "booking_success.html";
  }

  showToast(message, type = "info") {
    // Create toast notification
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 12px 20px;
      border-radius: 4px;
      color: white;
      z-index: 10000;
      font-weight: 500;
    `;

    // Set background color based on type
    const colors = {
      success: "#10b981",
      error: "#ef4444",
      warning: "#f59e0b",
      info: "#3b82f6",
    };
    toast.style.backgroundColor = colors[type] || colors.info;

    document.body.appendChild(toast);

    // Remove after 3 seconds
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 3000);
  }
}

// Initialize recommendations page
const recommendationsPage = new RecommendationsPage();
window.recommendationsPage = recommendationsPage;
