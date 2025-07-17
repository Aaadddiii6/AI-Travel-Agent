// Enhanced Travel Planner with OpenAI Integration
class TravelPlanner {
  constructor() {
    this.api = new APIService();
    this.currentStep = 1;
    this.totalSteps = 3;
    this.currentLevel = "continent";
    this.selectedContinent = null;
    this.selectedCountry = null;
    this.selectedCity = null;
    this.userPreferences = {};
    this.selectedDestinations = [];
    this.recommendations = null;
    this.uploadedPhotoUrl = null;
    this.destinationImages = {};
    this.init();
  }

  init() {
    this.loadUploadedPhoto();
    this.setupEventListeners();
    this.setupBudgetSlider();
    this.setupInterestCheckboxes();
    this.setupDatePickers();
    this.setupTabSwitching();
    this.updateProgress();
    this.loadContinents();
  }

  loadUploadedPhoto() {
    const savedPhotoUrl = sessionStorage.getItem("uploadedPhotoUrl");
    if (savedPhotoUrl) {
      this.uploadedPhotoUrl = savedPhotoUrl;
    }
  }

  setupEventListeners() {
    document
      .getElementById("generate-recommendations")
      ?.addEventListener("click", () => this.generateRecommendations());
    document
      .getElementById("back-to-preferences")
      ?.addEventListener("click", () => this.goToStep(1));
    document
      .getElementById("proceed-to-booking")
      ?.addEventListener("click", () => this.goToStep(3));
    document
      .getElementById("back-to-destinations")
      ?.addEventListener("click", () => this.goToStep(2));
    document
      .getElementById("complete-booking")
      ?.addEventListener("click", () => this.completeBooking());

    document
      .getElementById("search-flights")
      ?.addEventListener("click", () => this.searchFlights());
    document
      .getElementById("search-hotels")
      ?.addEventListener("click", () => this.searchHotels());

    document
      .getElementById("mood-filter")
      ?.addEventListener("change", (e) => this.applyFilters());
    document
      .getElementById("time-filter")
      ?.addEventListener("change", (e) => this.applyFilters());
    document
      .getElementById("people-filter")
      ?.addEventListener("change", (e) => this.applyFilters());
    document
      .getElementById("budget-filter")
      ?.addEventListener("change", (e) => this.applyFilters());
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

  setupDatePickers() {
    const dateInputs = document.querySelectorAll(".datepicker");
    if (typeof flatpickr !== "undefined") {
      dateInputs.forEach((input) => {
        flatpickr(input, {
          dateFormat: "Y-m-d",
          minDate: "today",
          disableMobile: true,
        });
      });
    }
  }

  setupTabSwitching() {
    const tabs = document.querySelectorAll(".booking-tab");
    const contents = document.querySelectorAll(".booking-content");

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        const tabName = tab.dataset.tab;
        tabs.forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        contents.forEach((content) => content.classList.remove("active"));
        document.getElementById(`${tabName}-tab`).classList.add("active");
      });
    });
  }

  getFormData() {
    const ageGroup = document.getElementById("ageGroup").value;
    const groupSize = document.getElementById("groupSize").value;
    const budgetRange = document.getElementById("budgetRange").value;
    const tripDuration = document.getElementById("tripDuration").value;
    const additionalNotes = document.getElementById("additionalNotes").value;

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
      budgetRange: parseInt(budgetRange),
      tripDuration,
      interests: selectedInterests,
      additionalNotes,
    };
  }

  validatePreferences() {
    const data = this.getFormData();

    if (!data.ageGroup) {
      uiComponents.showToast("Please select your age group", "error");
      return false;
    }

    if (!data.groupSize) {
      uiComponents.showToast("Please select your group size", "error");
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
    if (!this.validatePreferences()) {
      return;
    }

    this.userPreferences = this.getFormData();

    this.showLoadingState("step-1");

    try {
      const response = await this.api.generatePersonalizedRecommendations(
        this.userPreferences
      );

      if (response.success) {
        this.recommendations = response.data;
        this.displayRecommendations(response.data);
        this.goToStep(2);
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
      this.hideLoadingState("step-1");
    }
  }

  displayRecommendations(data) {
    const results = document.getElementById("recommendations-results");
    const content = document.getElementById("recommendations-content");

    if (!results || !content) return;

    let html = "";

    if (data.destinations && data.destinations.length > 0) {
      html += '<div class="recommendation-card">';
      html +=
        '<h4><i class="fas fa-map-marker-alt"></i> Recommended Destinations</h4>';
      html +=
        "<p>Based on your preferences, here are the perfect destinations for your trip:</p>";

      html += '<div class="location-selector">';
      html +=
        '<label for="selected-location">Choose your preferred destination:</label>';
      html += '<select id="selected-location" class="form-select">';
      html += '<option value="">Select a destination</option>';

      data.destinations.forEach((dest, index) => {
        html += `<option value="${dest.id}">${dest.name}, ${dest.country}</option>`;
      });

      html += "</select>";
      html +=
        '<button class="btn btn-primary" onclick="travelPlanner.selectRecommendedDestination()">Continue with Selection</button>';
      html += "</div>";

      data.destinations.forEach((dest, index) => {
        html += `
                    <div style="margin: 15px 0; padding: 15px; background: white; border-radius: 8px; border-left: 3px solid #3498db;">
                        <h5 style="margin: 0 0 10px 0; color: #2c3e50;">${
                          index + 1
                        }. ${dest.name}</h5>
                        <p style="margin: 0 0 8px 0; color: #7f8c8d;">${
                          dest.country
                        }, ${dest.continent}</p>
                        <p style="margin: 0; font-size: 14px;">${
                          dest.description
                        }</p>
                        <div style="margin-top: 10px;">
                            <span style="background: #e8f5e8; color: #27ae60; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-right: 10px;">
                                Rating: ${dest.rating}/5
                            </span>
                            <span style="background: #fff3cd; color: #856404; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                                Budget: ${dest.price}
                            </span>
                        </div>
                    </div>
                `;
      });

      html += "</div>";
    }

    if (data.itinerary && data.itinerary.length > 0) {
      html += '<div class="recommendation-card">';
      html += '<h4><i class="fas fa-calendar-alt"></i> Custom Itinerary</h4>';
      html +=
        "<p>Here's a personalized itinerary based on your interests and preferences:</p>";

      data.itinerary.forEach((day, index) => {
        html += `
                    <div class="itinerary-day">
                        <h5>Day ${index + 1}: ${day.title}</h5>
                        <ul>
                            ${day.activities
                              .map((activity) => `<li>${activity}</li>`)
                              .join("")}
                        </ul>
                    </div>
                `;
      });

      html += "</div>";
    }

    content.innerHTML = html;
    results.style.display = "block";
  }

  selectRecommendedDestination() {
    const selectedLocation = document.getElementById("selected-location").value;
    if (!selectedLocation) {
      uiComponents.showToast("Please select a destination", "error");
      return;
    }

    const destination = this.recommendations.destinations.find(
      (dest) => dest.id == selectedLocation
    );
    if (destination) {
      this.selectedDestinations = [destination];
      this.goToStep(2);
    }
  }

  async loadContinents() {
    try {
      this.showLoadingState("step-2");
      console.log("Loading continents...");
      const response = await this.api.getContinents();
      console.log("Continents response:", response);
      if (response.success) {
        this.renderContinents(response.data);
      } else {
        throw new Error("Failed to load continents");
      }
    } catch (error) {
      console.error("Failed to load continents:", error);
      uiComponents.showToast(
        "Failed to load continents: " + error.message,
        "error"
      );
    } finally {
      this.hideLoadingState("step-2");
    }
  }

  renderContinents(continents) {
    const grid = document.getElementById("destinations-grid");
    if (!grid) return;

    let html = "";
    (continents.data || []).forEach((continent, index) => {
      const imageUrl = `https://source.unsplash.com/400x200/?${encodeURIComponent(
        continent.name + " landscape"
      )}`;

      html += `
                <div class="destination-card continent-card" onclick="travelPlanner.selectContinent('${
                  continent.name
                }')">
                    <div class="destination-image" style="background-image: url('${imageUrl}'); background-size: cover; background-position: center;">
                        <div class="image-overlay">
                            <i class="fas fa-globe"></i>
                        </div>
                    </div>
                    <div class="destination-content">
                        <h3 class="destination-title">${continent.name}</h3>
                        <p class="destination-location">${
                          continent.count || 0
                        } destinations</p>
                        <p class="destination-description">${
                          continent.description ||
                          "Explore amazing destinations"
                        }</p>
                    </div>
                </div>
            `;
    });

    grid.innerHTML = html;
    grid.style.display = "grid";
  }

  async selectContinent(continentName) {
    console.log("Selecting continent:", continentName);
    this.selectedContinent = continentName;
    this.currentLevel = "country";

    try {
      this.showLoadingState("step-2");
      console.log("Loading countries for:", continentName);
      const response = await this.api.getCountriesByContinent(continentName);
      console.log("Countries response:", response);
      if (response.success) {
        this.renderCountries(response.data);
        this.updateStepIndicators(2);
      } else {
        throw new Error("Failed to load countries");
      }
    } catch (error) {
      console.error("Failed to load countries:", error);
      uiComponents.showToast(
        "Failed to load countries: " + error.message,
        "error"
      );
    } finally {
      this.hideLoadingState("step-2");
    }
  }

  renderCountries(countries) {
    const grid = document.getElementById("destinations-grid");
    if (!grid) return;

    let html = "";
    countries.forEach((country, index) => {
      const imageUrl = `https://source.unsplash.com/400x200/?${encodeURIComponent(
        country.name + " landscape"
      )}`;

      html += `
                <div class="destination-card country-card" onclick="travelPlanner.selectCountry('${
                  country.name
                }')">
                    <div class="destination-image" style="background-image: url('${imageUrl}'); background-size: cover; background-position: center;">
                        <div class="image-overlay">
                            <i class="fas fa-flag"></i>
                        </div>
                    </div>
                    <div class="destination-content">
                        <h3 class="destination-title">${country.name}</h3>
                        <p class="destination-location">${
                          country.cities?.length || 0
                        } cities</p>
                        <p class="destination-description">${
                          country.description || "Discover amazing cities"
                        }</p>
                    </div>
                </div>
            `;
    });

    grid.innerHTML = html;
  }

  async selectCountry(countryName) {
    console.log("Selecting country:", countryName);
    this.selectedCountry = countryName;
    this.currentLevel = "city";

    try {
      this.showLoadingState("step-2");
      console.log("Loading cities for:", countryName);
      const response = await this.api.getCitiesByCountry(countryName);
      console.log("Cities response:", response);
      if (response.success) {
        this.renderCities(response.data);
        this.updateStepIndicators(3);
      } else {
        throw new Error("Failed to load cities");
      }
    } catch (error) {
      console.error("Failed to load cities:", error);
      uiComponents.showToast(
        "Failed to load cities: " + error.message,
        "error"
      );
    } finally {
      this.hideLoadingState("step-2");
    }
  }

  renderCities(cities) {
    const grid = document.getElementById("destinations-grid");
    if (!grid) return;

    let html = "";
    cities.forEach((city, index) => {
      const imageUrl = `https://source.unsplash.com/400x200/?${encodeURIComponent(
        city.name + " city"
      )}`;

      html += `
                <div class="destination-card city-card" onclick="travelPlanner.selectCity('${
                  city.name
                }')">
                    <div class="destination-image" style="background-image: url('${imageUrl}'); background-size: cover; background-position: center;">
                        <div class="image-overlay">
                            <i class="fas fa-city"></i>
                        </div>
                    </div>
                    <div class="destination-content">
                        <h3 class="destination-title">${city.name}</h3>
                        <p class="destination-location">${
                          city.areas?.length || 0
                        } areas</p>
                        <p class="destination-description">${
                          city.description || "Explore local areas"
                        }</p>
                        <div class="destination-actions">
                            <button class="btn btn-primary btn-sm" onclick="event.stopPropagation(); travelPlanner.generateItinerary('${
                              city.id
                            }')">
                                <i class="fas fa-calendar"></i> Generate Itinerary
                            </button>
                            <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); travelPlanner.generateImage('${
                              city.id
                            }')">
                                <i class="fas fa-image"></i> Generate Image
                            </button>
                        </div>
                    </div>
                </div>
            `;
    });

    grid.innerHTML = html;
  }

  async selectCity(cityName) {
    console.log("Selecting city:", cityName);
    this.selectedCity = cityName;
    this.currentLevel = "area";

    try {
      this.showLoadingState("step-2");
      console.log("Loading areas for:", cityName);
      const response = await this.api.getAreasByCity(cityName);
      console.log("Areas response:", response);
      if (response.success) {
        this.renderAreas(response.data);
        this.updateStepIndicators(4);
      } else {
        throw new Error("Failed to load areas");
      }
    } catch (error) {
      console.error("Failed to load areas:", error);
      uiComponents.showToast("Failed to load areas: " + error.message, "error");
    } finally {
      this.hideLoadingState("step-2");
    }
  }

  renderAreas(areas) {
    const grid = document.getElementById("destinations-grid");
    if (!grid) return;

    let html = "";
    areas.forEach((area, index) => {
      const imageUrl = `https://source.unsplash.com/400x200/?${encodeURIComponent(
        area.name + " neighborhood"
      )}`;

      html += `
                <div class="destination-card area-card" onclick="travelPlanner.selectArea('${
                  area.name
                }')">
                    <div class="destination-image" style="background-image: url('${imageUrl}'); background-size: cover; background-position: center;">
                        <div class="image-overlay">
                            <i class="fas fa-map-marker-alt"></i>
                        </div>
                    </div>
                    <div class="destination-content">
                        <h3 class="destination-title">${area.name}</h3>
                        <p class="destination-location">${
                          area.activities?.length || 0
                        } activities</p>
                        <p class="destination-description">${
                          area.description || "Discover local experiences"
                        }</p>
                        <div class="destination-actions">
                            <button class="btn btn-primary btn-sm" onclick="event.stopPropagation(); travelPlanner.generateItinerary('${
                              area.id
                            }')">
                                <i class="fas fa-calendar"></i> Generate Itinerary
                            </button>
                            <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); travelPlanner.generateImage('${
                              area.id
                            }')">
                                <i class="fas fa-image"></i> Generate Image
                            </button>
                        </div>
                    </div>
                </div>
            `;
    });

    grid.innerHTML = html;
  }

  selectArea(areaName) {
    // Add the selected area to destinations and proceed to booking
    const selectedArea = {
      id: areaName.toLowerCase().replace(/\s+/g, "-"),
      name: areaName,
      type: "area",
      city: this.selectedCity,
      country: this.selectedCountry,
      continent: this.selectedContinent,
    };

    this.selectedDestinations = [selectedArea];
    this.goToStep(3);
  }

  async generateItinerary(destinationId) {
    try {
      uiComponents.showToast(
        "Generating personalized itinerary with AI...",
        "info"
      );
      const response = await this.api.generateItinerary(
        destinationId,
        this.userPreferences
      );
      if (response.success) {
        this.displayItinerary(response.data);
      } else {
        throw new Error("Failed to generate itinerary");
      }
    } catch (error) {
      console.error("Failed to generate itinerary:", error);
      uiComponents.showToast(
        "Failed to generate itinerary: " + error.message,
        "error"
      );
    }
  }

  async generateImage(destinationId) {
    if (!this.uploadedPhotoUrl) {
      uiComponents.showToast("Please upload a photo first", "error");
      return;
    }

    try {
      uiComponents.showToast(
        "Generating AI travel photo with OpenAI...",
        "info"
      );
      const response = await this.api.generateDestinationImage(
        destinationId,
        this.uploadedPhotoUrl
      );
      if (response.success) {
        this.displayGeneratedImage(response.data);
      } else {
        throw new Error("Failed to generate image");
      }
    } catch (error) {
      console.error("Failed to generate image:", error);
      uiComponents.showToast(
        "Failed to generate image: " + error.message,
        "error"
      );
    }
  }

  displayItinerary(itinerary) {
    const modal = document.createElement("div");
    modal.className = "modal";
    modal.innerHTML = `
            <div class="modal-content">
                <span class="close">&times;</span>
                <h2>Your Custom AI-Generated Itinerary</h2>
                <div class="itinerary-content">
                    ${itinerary.days
                      .map(
                        (day, index) => `
                        <div class="itinerary-day">
                            <h3>Day ${index + 1}: ${day.title}</h3>
                            <ul>
                                ${day.activities
                                  .map((activity) => `<li>${activity}</li>`)
                                  .join("")}
                            </ul>
                        </div>
                    `
                      )
                      .join("")}
                </div>
            </div>
        `;

    document.body.appendChild(modal);

    modal.querySelector(".close").onclick = () => modal.remove();
    modal.onclick = (e) => {
      if (e.target === modal) modal.remove();
    };
  }

  displayGeneratedImage(imageData) {
    const modal = document.createElement("div");
    modal.className = "modal";
    modal.innerHTML = `
            <div class="modal-content">
                <span class="close">&times;</span>
                <h2>Your AI-Generated Travel Photo</h2>
                <div class="image-content">
                    <img src="${imageData.url}" alt="AI Generated Travel Photo" style="width: 100%; max-width: 500px; border-radius: 10px;">
                    <p style="margin-top: 15px; color: #7f8c8d;">Generated with OpenAI DALL-E</p>
                </div>
            </div>
        `;

    document.body.appendChild(modal);

    modal.querySelector(".close").onclick = () => modal.remove();
    modal.onclick = (e) => {
      if (e.target === modal) modal.remove();
    };
  }

  async goToStep(step) {
    if (step === 2 && !this.recommendations) {
      uiComponents.showToast("Please generate recommendations first", "error");
      return;
    }

    if (step === 3 && this.selectedDestinations.length === 0) {
      uiComponents.showToast("Please select at least one destination", "error");
      return;
    }

    document.querySelectorAll(".planner-section").forEach((section) => {
      section.classList.remove("active");
    });

    document.getElementById(`step-${step}`).classList.add("active");
    this.updateStepIndicators(step);
    this.currentStep = step;
    this.updateProgress();

    if (step === 2) {
      await this.loadContinents();
    } else if (step === 3) {
      this.setupBookingDefaults();
    }
  }

  updateStepIndicators(activeStep) {
    document.querySelectorAll(".step-indicator").forEach((indicator, index) => {
      const stepNumber = index + 1;
      indicator.classList.remove("active", "completed");

      if (stepNumber < activeStep) {
        indicator.classList.add("completed");
      } else if (stepNumber === activeStep) {
        indicator.classList.add("active");
      }
    });
  }

  updateProgress() {
    const progress = (this.currentStep / this.totalSteps) * 100;
    document.getElementById("progress-bar").style.width = `${progress}%`;
  }

  showLoadingState(stepId) {
    const section = document.getElementById(stepId);
    const loadingState = section.querySelector(".loading-state");
    if (loadingState) {
      loadingState.style.display = "block";
    }
  }

  hideLoadingState(stepId) {
    const section = document.getElementById(stepId);
    const loadingState = section.querySelector(".loading-state");
    if (loadingState) {
      loadingState.style.display = "none";
    }
  }

  setupBookingDefaults() {
    if (this.selectedDestinations.length > 0) {
      const hotelDestination = document.getElementById("hotel-destination");
      const flightTo = document.getElementById("flight-to");

      if (hotelDestination) {
        hotelDestination.value = this.selectedDestinations[0].name;
      }
      if (flightTo) {
        flightTo.value = this.selectedDestinations[0].name;
      }
    }

    if (this.userPreferences.groupSize) {
      const passengers = document.getElementById("flight-passengers");
      const guests = document.getElementById("hotel-guests");

      const groupSizeMap = {
        solo: "1",
        couple: "2",
        family: "4",
        friends: "4",
        "large-group": "5",
      };

      const size = groupSizeMap[this.userPreferences.groupSize];
      if (passengers) passengers.value = size;
      if (guests) guests.value = size;
    }
  }

  async searchFlights() {
    const from = document.getElementById("flight-from").value;
    const to = document.getElementById("flight-to").value;
    const depart = document.getElementById("flight-depart").value;

    if (!from || !to || !depart) {
      uiComponents.showToast(
        "Please fill in all required flight details",
        "error"
      );
      return;
    }

    const results = document.getElementById("flight-results");
    results.style.display = "block";
    results.innerHTML =
      '<div class="loading-state"><div class="loading-spinner"></div><p>Searching for flights with Amadeus API...</p></div>';

    try {
      const response = await this.api.searchFlights({
        origin: from,
        destination: to,
        departureDate: depart,
        returnDate: document.getElementById("flight-return").value,
        adults: document.getElementById("flight-passengers").value,
      });

      if (response.success) {
        this.displayFlightResults(response.data);
      } else {
        throw new Error("Failed to search flights");
      }
    } catch (error) {
      console.error("Flight search failed:", error);
      uiComponents.showToast(
        "Failed to search flights: " + error.message,
        "error"
      );
    }
  }

  async searchHotels() {
    const destination = document.getElementById("hotel-destination").value;
    const checkin = document.getElementById("hotel-checkin").value;
    const checkout = document.getElementById("hotel-checkout").value;

    if (!destination || !checkin || !checkout) {
      uiComponents.showToast(
        "Please fill in all required hotel details",
        "error"
      );
      return;
    }

    const results = document.getElementById("hotel-results");
    results.style.display = "block";
    results.innerHTML =
      '<div class="loading-state"><div class="loading-spinner"></div><p>Searching for hotels with Amadeus API...</p></div>';

    try {
      const response = await this.api.searchHotels({
        cityCode: destination,
        checkInDate: checkin,
        checkOutDate: checkout,
        adults: document.getElementById("hotel-guests").value,
      });

      if (response.success) {
        this.displayHotelResults(response.data);
      } else {
        throw new Error("Failed to search hotels");
      }
    } catch (error) {
      console.error("Hotel search failed:", error);
      uiComponents.showToast(
        "Failed to search hotels: " + error.message,
        "error"
      );
    }
  }

  displayFlightResults(flights) {
    const grid = document.getElementById("flight-results-grid");
    if (!grid) return;

    let html = "";
    flights.forEach((flight) => {
      html += `
                <div class="flight-card" style="background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h4 style="margin: 0;">${flight.airline}</h4>
                        <span style="background: #e8f5e8; color: #27ae60; padding: 4px 8px; border-radius: 4px; font-weight: 600;">
                            $${flight.price}
                        </span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <div>
                            <strong>${flight.departure}</strong>
                            <p style="margin: 5px 0; color: #7f8c8d;">${flight.departureTime}</p>
                        </div>
                        <div style="text-align: center;">
                            <i class="fas fa-plane" style="color: #3498db;"></i>
                            <p style="margin: 5px 0; font-size: 12px; color: #7f8c8d;">${flight.duration}</p>
                        </div>
                        <div style="text-align: right;">
                            <strong>${flight.arrival}</strong>
                            <p style="margin: 5px 0; color: #7f8c8d;">${flight.arrivalTime}</p>
                        </div>
                    </div>
                    <button class="btn btn-primary" style="width: 100%;" onclick="travelPlanner.bookFlight('${flight.id}')">
                        Book Flight
                    </button>
                </div>
            `;
    });

    grid.innerHTML = html;
  }

  displayHotelResults(hotels) {
    const grid = document.getElementById("hotel-results-grid");
    if (!grid) return;

    let html = "";
    hotels.forEach((hotel) => {
      html += `
                <div class="hotel-card" style="background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h4 style="margin: 0;">${hotel.name}</h4>
                        <span style="background: #e8f5e8; color: #27ae60; padding: 4px 8px; border-radius: 4px; font-weight: 600;">
                            $${hotel.price}/night
                        </span>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <div style="color: #f39c12; margin-bottom: 5px;">${this.generateStars(
                          hotel.rating
                        )} ${hotel.rating}/5</div>
                        <p style="margin: 5px 0; color: #7f8c8d;">${
                          hotel.location
                        }</p>
                        <p style="margin: 5px 0; font-size: 14px;">${hotel.amenities.join(
                          ", "
                        )}</p>
                    </div>
                    <button class="btn btn-primary" style="width: 100%;" onclick="travelPlanner.bookHotel('${
                      hotel.id
                    }')">
                        Book Hotel
                    </button>
                </div>
            `;
    });

    grid.innerHTML = html;
  }

  generateStars(rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);

    return (
      "★".repeat(fullStars) + (hasHalfStar ? "☆" : "") + "☆".repeat(emptyStars)
    );
  }

  bookFlight(flightId) {
    uiComponents.showToast(
      `Flight ${flightId} booked successfully!`,
      "success"
    );
    document.getElementById("complete-booking").disabled = false;
  }

  bookHotel(hotelId) {
    uiComponents.showToast(`Hotel ${hotelId} booked successfully!`, "success");
    document.getElementById("complete-booking").disabled = false;
  }

  completeBooking() {
    document.querySelectorAll(".planner-section").forEach((section) => {
      section.classList.remove("active");
    });

    document.getElementById("success-step").style.display = "block";
    this.updateProgress();
  }

  applyFilters() {
    const mood = document.getElementById("mood-filter")?.value;
    const time = document.getElementById("time-filter")?.value;
    const people = document.getElementById("people-filter")?.value;
    const budget = document.getElementById("budget-filter")?.value;

    this.filterDestinationsByCriteria({ mood, time, people, budget });
  }

  async filterDestinationsByCriteria(criteria) {
    try {
      const response = await this.api.filterDestinations(criteria);
      if (response.success) {
        this.renderFilteredDestinations(response.data);
      }
    } catch (error) {
      console.error("Failed to filter destinations:", error);
      uiComponents.showToast(
        "Failed to filter destinations: " + error.message,
        "error"
      );
    }
  }

  renderFilteredDestinations(destinations) {
    if (this.currentLevel === "continent") {
      this.renderContinents(destinations);
    } else if (this.currentLevel === "country") {
      this.renderCountries(destinations);
    } else if (this.currentLevel === "city") {
      this.renderCities(destinations);
    } else if (this.currentLevel === "area") {
      this.renderAreas(destinations);
    }
  }
}

// Initialize the travel planner when the page loads
let travelPlanner;
document.addEventListener("DOMContentLoaded", function () {
  travelPlanner = new TravelPlanner();
});

// Global function to reset planner
function resetPlanner() {
  location.reload();
}
