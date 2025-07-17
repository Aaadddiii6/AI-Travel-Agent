// Booking Page JavaScript - Enhanced with OpenAI API integration

document.addEventListener("DOMContentLoaded", function () {
  // Initialize date pickers
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

  // Initialize autocomplete for destination inputs
  initializeAutocomplete();

  // Tab switching functionality
  const tabs = document.querySelectorAll(".booking-tab");
  const contents = document.querySelectorAll(".booking-content");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const tabName = tab.dataset.tab;

      // Update active tab
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");

      // Update active content
      contents.forEach((content) => content.classList.remove("active"));
      document.getElementById(`${tabName}-tab`).classList.add("active");
    });
  });

  // Search functionality
  const searchButtons = {
    flights: document.getElementById("search-flights"),
    hotels: document.getElementById("search-hotels"),
    activities: document.getElementById("search-activities"),
    packages: document.getElementById("search-packages"),
    agents: document.getElementById("search-agents"),
  };

  Object.entries(searchButtons).forEach(([type, button]) => {
    if (button) {
      button.addEventListener("click", () => performSearch(type));
    }
  });

  // Quick actions
  const quickActionButtons = document.querySelectorAll(".quick-action-btn");
  quickActionButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const destination = button.dataset.destination;
      handleQuickAction(destination);
    });
  });

  function handleQuickAction(destination) {
    const destinationMap = {
      paris: { tab: "hotels", city: "Paris, France" },
      tokyo: { tab: "activities", city: "Tokyo, Japan" },
      bali: { tab: "packages", city: "Bali, Indonesia" },
      "new-york": { tab: "flights", city: "New York, USA" },
      dubai: { tab: "hotels", city: "Dubai, UAE" },
      santorini: { tab: "packages", city: "Santorini, Greece" },
    };

    const config = destinationMap[destination];
    if (config) {
      // Switch to appropriate tab
      const tab = document.querySelector(`[data-tab="${config.tab}"]`);
      if (tab) {
        tabs.forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");

        contents.forEach((content) => content.classList.remove("active"));
        document.getElementById(`${config.tab}-tab`).classList.add("active");
      }

      // Fill destination field
      const destinationInput = document.getElementById(
        `${config.tab}-destination`
      );
      if (destinationInput) {
        destinationInput.value = config.city;
      }

      // Perform search
      setTimeout(() => {
        performSearch(config.tab);
      }, 100);
    }
  }

  // Autocomplete functionality
  function initializeAutocomplete() {
    const destinationInputs = [
      "flight-from",
      "flight-to",
      "hotel-destination",
      "activity-destination",
    ];

    destinationInputs.forEach((inputId) => {
      const input = document.getElementById(inputId);
      if (input) {
        let suggestionsContainer = null;
        let debounceTimer = null;

        input.addEventListener("input", function () {
          const query = this.value.trim();

          // Clear previous timer
          if (debounceTimer) {
            clearTimeout(debounceTimer);
          }

          // Remove existing suggestions
          if (suggestionsContainer) {
            suggestionsContainer.remove();
            suggestionsContainer = null;
          }

          // Don't search if query is too short
          if (query.length < 2) {
            return;
          }

          // Debounce the API call
          debounceTimer = setTimeout(async () => {
            try {
              // For flight search, show airport codes
              if (input.id === "flight-from" || input.id === "flight-to") {
                const airportSuggestions = getAirportSuggestions(query);
                if (airportSuggestions.length > 0) {
                  showSuggestions(input, airportSuggestions);
                }
              } else if (input.id === "hotel-destination") {
                // For hotel search, show city codes
                const citySuggestions = getCitySuggestions(query);
                if (citySuggestions.length > 0) {
                  showSuggestions(input, citySuggestions);
                }
              } else {
                // For other fields, use the API
                const response = await fetch(
                  `http://localhost:8000/api/destination-suggestions?query=${encodeURIComponent(
                    query
                  )}`
                );
                const data = await response.json();

                if (data.suggestions && data.suggestions.length > 0) {
                  showSuggestions(input, data.suggestions);
                }
              }
            } catch (error) {
              console.error("Autocomplete error:", error);
            }
          }, 300);
        });

        // Hide suggestions when clicking outside
        document.addEventListener("click", function (e) {
          if (
            suggestionsContainer &&
            !input.contains(e.target) &&
            !suggestionsContainer.contains(e.target)
          ) {
            suggestionsContainer.remove();
            suggestionsContainer = null;
          }
        });
      }
    });
  }

  function getAirportSuggestions(query) {
    const airports = [
      {
        code: "JFK",
        name: "John F. Kennedy International Airport",
        city: "New York",
      },
      {
        code: "LAX",
        name: "Los Angeles International Airport",
        city: "Los Angeles",
      },
      { code: "ORD", name: "O'Hare International Airport", city: "Chicago" },
      {
        code: "DFW",
        name: "Dallas/Fort Worth International Airport",
        city: "Dallas",
      },
      {
        code: "ATL",
        name: "Hartsfield-Jackson Atlanta International Airport",
        city: "Atlanta",
      },
      { code: "DEN", name: "Denver International Airport", city: "Denver" },
      {
        code: "SFO",
        name: "San Francisco International Airport",
        city: "San Francisco",
      },
      {
        code: "LAS",
        name: "McCarran International Airport",
        city: "Las Vegas",
      },
      { code: "MCO", name: "Orlando International Airport", city: "Orlando" },
      {
        code: "CLT",
        name: "Charlotte Douglas International Airport",
        city: "Charlotte",
      },
      {
        code: "DEL",
        name: "Indira Gandhi International Airport",
        city: "Delhi",
      },
      {
        code: "BOM",
        name: "Chhatrapati Shivaji Maharaj International Airport",
        city: "Mumbai",
      },
      {
        code: "BLR",
        name: "Kempegowda International Airport",
        city: "Bangalore",
      },
      { code: "MAA", name: "Chennai International Airport", city: "Chennai" },
      {
        code: "HYD",
        name: "Rajiv Gandhi International Airport",
        city: "Hyderabad",
      },
      { code: "LHR", name: "Heathrow Airport", city: "London" },
      { code: "CDG", name: "Charles de Gaulle Airport", city: "Paris" },
      { code: "FRA", name: "Frankfurt Airport", city: "Frankfurt" },
      { code: "AMS", name: "Amsterdam Airport Schiphol", city: "Amsterdam" },
      { code: "NRT", name: "Narita International Airport", city: "Tokyo" },
      { code: "HND", name: "Haneda Airport", city: "Tokyo" },
      {
        code: "PEK",
        name: "Beijing Capital International Airport",
        city: "Beijing",
      },
      {
        code: "PVG",
        name: "Shanghai Pudong International Airport",
        city: "Shanghai",
      },
      { code: "SYD", name: "Sydney Airport", city: "Sydney" },
      { code: "MEL", name: "Melbourne Airport", city: "Melbourne" },
      { code: "DXB", name: "Dubai International Airport", city: "Dubai" },
      { code: "SIN", name: "Singapore Changi Airport", city: "Singapore" },
      { code: "BKK", name: "Suvarnabhumi Airport", city: "Bangkok" },
      {
        code: "KUL",
        name: "Kuala Lumpur International Airport",
        city: "Kuala Lumpur",
      },
    ];

    const queryLower = query.toLowerCase();
    return airports
      .filter(
        (airport) =>
          airport.code.toLowerCase().includes(queryLower) ||
          airport.city.toLowerCase().includes(queryLower) ||
          airport.name.toLowerCase().includes(queryLower)
      )
      .map((airport) => `${airport.code} - ${airport.city} (${airport.name})`)
      .slice(0, 10); // Limit to 10 suggestions
  }

  function getCitySuggestions(query) {
    const cities = [
      { code: "NYC", name: "New York City", country: "USA" },
      { code: "LAX", name: "Los Angeles", country: "USA" },
      { code: "CHI", name: "Chicago", country: "USA" },
      { code: "MIA", name: "Miami", country: "USA" },
      { code: "LAS", name: "Las Vegas", country: "USA" },
      { code: "SFO", name: "San Francisco", country: "USA" },
      { code: "BOS", name: "Boston", country: "USA" },
      { code: "SEA", name: "Seattle", country: "USA" },
      { code: "DEN", name: "Denver", country: "USA" },
      { code: "ATL", name: "Atlanta", country: "USA" },
      { code: "DEL", name: "Delhi", country: "India" },
      { code: "BOM", name: "Mumbai", country: "India" },
      { code: "BLR", name: "Bangalore", country: "India" },
      { code: "MAA", name: "Chennai", country: "India" },
      { code: "HYD", name: "Hyderabad", country: "India" },
      { code: "CCU", name: "Kolkata", country: "India" },
      { code: "LON", name: "London", country: "UK" },
      { code: "PAR", name: "Paris", country: "France" },
      { code: "BER", name: "Berlin", country: "Germany" },
      { code: "MAD", name: "Madrid", country: "Spain" },
      { code: "ROM", name: "Rome", country: "Italy" },
      { code: "AMS", name: "Amsterdam", country: "Netherlands" },
      { code: "VIE", name: "Vienna", country: "Austria" },
      { code: "ZRH", name: "Zurich", country: "Switzerland" },
      { code: "TOK", name: "Tokyo", country: "Japan" },
      { code: "OSA", name: "Osaka", country: "Japan" },
      { code: "SEL", name: "Seoul", country: "South Korea" },
      { code: "PEK", name: "Beijing", country: "China" },
      { code: "SHA", name: "Shanghai", country: "China" },
      { code: "HKG", name: "Hong Kong", country: "China" },
      { code: "SIN", name: "Singapore", country: "Singapore" },
      { code: "BKK", name: "Bangkok", country: "Thailand" },
      { code: "KUL", name: "Kuala Lumpur", country: "Malaysia" },
      { code: "JAK", name: "Jakarta", country: "Indonesia" },
      { code: "MNL", name: "Manila", country: "Philippines" },
      { code: "HAN", name: "Hanoi", country: "Vietnam" },
      { code: "SYD", name: "Sydney", country: "Australia" },
      { code: "MEL", name: "Melbourne", country: "Australia" },
      { code: "AKL", name: "Auckland", country: "New Zealand" },
      { code: "DXB", name: "Dubai", country: "UAE" },
      { code: "DOH", name: "Doha", country: "Qatar" },
      { code: "JED", name: "Jeddah", country: "Saudi Arabia" },
      { code: "CAI", name: "Cairo", country: "Egypt" },
      { code: "JNB", name: "Johannesburg", country: "South Africa" },
      { code: "NBO", name: "Nairobi", country: "Kenya" },
      { code: "LAG", name: "Lagos", country: "Nigeria" },
      { code: "SAO", name: "São Paulo", country: "Brazil" },
      { code: "RIO", name: "Rio de Janeiro", country: "Brazil" },
      { code: "BUE", name: "Buenos Aires", country: "Argentina" },
      { code: "MEX", name: "Mexico City", country: "Mexico" },
      { code: "GDL", name: "Guadalajara", country: "Mexico" },
      { code: "MTY", name: "Monterrey", country: "Mexico" },
      { code: "LIM", name: "Lima", country: "Peru" },
      { code: "BOG", name: "Bogotá", country: "Colombia" },
      { code: "CCS", name: "Caracas", country: "Venezuela" },
      { code: "SCL", name: "Santiago", country: "Chile" },
      { code: "MVD", name: "Montevideo", country: "Uruguay" },
      { code: "ASU", name: "Asunción", country: "Paraguay" },
    ];

    const queryLower = query.toLowerCase();
    return cities
      .filter(
        (city) =>
          city.code.toLowerCase().includes(queryLower) ||
          city.name.toLowerCase().includes(queryLower) ||
          city.country.toLowerCase().includes(queryLower)
      )
      .map((city) => `${city.code} - ${city.name}, ${city.country}`)
      .slice(0, 10); // Limit to 10 suggestions
  }

  function showSuggestions(input, suggestions) {
    // Remove existing suggestions
    const existing = document.querySelector(".suggestions-container");
    if (existing) {
      existing.remove();
    }

    // Create suggestions container
    const container = document.createElement("div");
    container.className = "suggestions-container";
    container.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border: 1px solid #e1e5e9;
            border-top: none;
            border-radius: 0 0 8px 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            z-index: 1000;
            max-height: 200px;
            overflow-y: auto;
        `;

    suggestions.forEach((suggestion) => {
      const item = document.createElement("div");
      item.className = "suggestion-item";
      item.style.cssText = `
                padding: 12px 16px;
                cursor: pointer;
                border-bottom: 1px solid #f0f0f0;
                transition: background-color 0.2s;
            `;
      item.textContent = suggestion;

      item.addEventListener("mouseenter", () => {
        item.style.backgroundColor = "#f8f9fa";
      });

      item.addEventListener("mouseleave", () => {
        item.style.backgroundColor = "white";
      });

      item.addEventListener("click", () => {
        input.value = suggestion;
        container.remove();
      });

      container.appendChild(item);
    });

    // Position the container
    const inputRect = input.getBoundingClientRect();
    container.style.top = `${inputRect.bottom}px`;
    container.style.left = `${inputRect.left}px`;
    container.style.width = `${inputRect.width}px`;

    document.body.appendChild(container);

    // Store reference for cleanup
    const inputId = input.id;
    window[`suggestions_${inputId}`] = container;
  }

  async function performSearch(type) {
    const searchButton = document.getElementById(`search-${type}`);
    const resultsGrid = document.getElementById(`${type}-results-grid`);

    if (searchButton) {
      searchButton.disabled = true;
      searchButton.innerHTML =
        '<i class="fas fa-spinner fa-spin"></i> Searching...';
    }

    if (resultsGrid) {
      resultsGrid.innerHTML = `
                <div class="loading-state">
                    <div class="loading-spinner"></div>
                    <div class="loading-text">Searching for ${type}...</div>
                    <div class="loading-subtext">This may take a few moments</div>
                </div>
            `;
    }

    try {
      let data;

      if (type === "flights") {
        // Use the new Amadeus flight search endpoint
        const searchData = getFlightSearchData();

        // Debug: Log the search data
        console.log("Flight search data:", searchData);

        const response = await fetch(
          "http://localhost:8000/api/search-flights",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(searchData),
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        data = await response.json();
        console.log("Flight search response:", data);

        if (data.success && data.flights && data.flights.length > 0) {
          console.log(`Found ${data.flights.length} flights from ${data.provider || 'API'}`);
          displayResults(type, data.flights);
          showToast(
            `Found ${data.flights.length} flight options! (${data.provider || 'API'})`,
            "success"
          );
        } else {
          console.log("No flights found in API response, using mock data");
          // Fallback to mock data if no results
          const mockResults = getMockResults(type);
          displayResults(type, mockResults);
          showToast(
            `Found ${mockResults.length} flight options! (mock data)`,
            "success"
          );
        }
      } else if (type === "hotels") {
        // Use the new Amadeus hotel search endpoint
        const searchData = getHotelSearchData();

        // Debug: Log the search data
        console.log("Hotel search data:", searchData);

        // Validate required fields
        if (
          !searchData.city_code ||
          !searchData.check_in_date ||
          !searchData.check_out_date
        ) {
          showToast("Please fill in all required hotel search fields", "error");
          return;
        }

        const response = await fetch(
          "http://localhost:8000/api/search-hotels",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(searchData),
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        data = await response.json();
        console.log("Hotel search response:", data);

        if (data.success && data.hotels && data.hotels.length > 0) {
          console.log(`Found ${data.hotels.length} hotels from Amadeus API`);
          displayResults(type, data.hotels);
          showToast(
            `Found ${data.hotels.length} hotel options! (Amadeus API)`,
            "success"
          );
        } else {
          console.log("No hotels found in API response, using mock data");
          // Fallback to mock data if no results
          const mockResults = getMockResults(type);
          displayResults(type, mockResults);
          showToast(
            `Found ${mockResults.length} hotel options! (mock data)`,
            "success"
          );
        }
      } else {
        // Use the existing endpoint for other types
        const searchData = getSearchData(type);
        const response = await fetch(
          "http://localhost:8000/api/search-bookings",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(searchData),
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        data = await response.json();

        if (data.results && data.results.length > 0) {
          displayResults(type, data.results);
          showToast(
            `Found ${data.results.length} ${type} options! (${data.provider})`,
            "success"
          );
        } else {
          // Fallback to mock data if no results
          const mockResults = getMockResults(type);
          displayResults(type, mockResults);
          showToast(
            `Found ${mockResults.length} ${type} options! (mock data)`,
            "success"
          );
        }
      }
    } catch (error) {
      console.error("Search error:", error);
      showToast("Search failed. Using mock data...", "warning");

      // Fallback to mock data
      const mockResults = getMockResults(type);
      displayResults(type, mockResults);
    } finally {
      if (searchButton) {
        searchButton.disabled = false;
        searchButton.innerHTML =
          '<i class="fas fa-search"></i> Search ' +
          type.charAt(0).toUpperCase() +
          type.slice(1);
      }
    }
  }

  function getFlightSearchData() {
    // Get raw input values
    const originInput = document.getElementById("flight-from")?.value || "";
    const destinationInput = document.getElementById("flight-to")?.value || "";
    
    // Extract airport codes (handle formats like "JFK - New York" -> "JFK")
    let origin = originInput.toUpperCase();
    let destination = destinationInput.toUpperCase();
    
    // Extract 3-letter airport codes from the beginning of the string
    // Handle formats like: "JFK - New York", "BOM - MUMBAI (CHHATRAPATI SHIVAJI MAHARAJ INTERNATIONAL AIRPORT)"
    if (origin.includes(" - ")) {
      origin = origin.split(" - ")[0].trim();
    }
    if (destination.includes(" - ")) {
      destination = destination.split(" - ")[0].trim();
    }
    
    // Additional cleanup - remove any extra text after the 3-letter code
    origin = origin.substring(0, 3);
    destination = destination.substring(0, 3);
    
    // Validate airport codes (must be 3 letters)
    if (origin.length !== 3 || destination.length !== 3) {
      console.warn(`Invalid airport codes: ${origin} -> ${destination}`);
    }
    
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

  function getHotelSearchData() {
    // Format data specifically for the Amadeus API
    const hotelDestination =
      document.getElementById("hotel-destination")?.value || "";

    // Extract city code from the input (e.g., "NYC - New York City, USA" -> "NYC")
    let cityCode = hotelDestination;
    if (hotelDestination.includes(" - ")) {
      cityCode = hotelDestination.split(" - ")[0];
    }

    const data = {
      city_code: cityCode.toUpperCase(),
      check_in_date: document.getElementById("hotel-checkin")?.value || "",
      check_out_date: document.getElementById("hotel-checkout")?.value || "",
      adults: parseInt(document.getElementById("hotel-guests")?.value || 1),
      children: 0,
      room_quantity: parseInt(
        document.getElementById("hotel-rooms")?.value || 1
      ),
      currency_code: "USD",
    };

    console.log("Hotel search data being sent:", data);
    return data;
  }

  function getSearchData(type) {
    const data = {
      search_type: type,
      passengers: 1,
      class_type: "economy",
    };

    switch (type) {
      case "flights":
        data.from_location =
          document.getElementById("flight-from")?.value || null;
        data.to_location = document.getElementById("flight-to")?.value || null;
        data.departure_date =
          document.getElementById("flight-depart")?.value || null;
        data.return_date =
          document.getElementById("flight-return")?.value || null;
        data.passengers = parseInt(
          document.getElementById("flight-passengers")?.value || 1
        );
        data.class_type =
          document.getElementById("flight-class")?.value || "economy";
        break;

      case "hotels":
        data.to_location =
          document.getElementById("hotel-destination")?.value || null;
        data.departure_date =
          document.getElementById("hotel-checkin")?.value || null;
        data.return_date =
          document.getElementById("hotel-checkout")?.value || null;
        data.passengers = parseInt(
          document.getElementById("hotel-guests")?.value || 1
        );
        break;

      case "activities":
        data.to_location =
          document.getElementById("activity-destination")?.value || null;
        data.departure_date =
          document.getElementById("activity-date")?.value || null;
        data.passengers = parseInt(
          document.getElementById("activity-participants")?.value || 1
        );
        break;

      case "packages":
        data.from_location =
          document.getElementById("package-from")?.value || null;
        data.to_location = document.getElementById("package-to")?.value || null;
        data.departure_date =
          document.getElementById("package-depart")?.value || null;
        data.return_date =
          document.getElementById("package-return")?.value || null;
        data.passengers = parseInt(
          document.getElementById("package-travelers")?.value || 1
        );
        break;
    }

    return data;
  }

  function displayResults(type, results) {
    console.log(`Displaying ${type} results:`, results);

    // Map the type to the correct element ID
    const elementIdMap = {
      flights: "flight-results-grid",
      hotels: "hotel-results-grid",
      activities: "activity-results-grid",
      packages: "package-results-grid",
      agents: "agent-results-grid",
    };

    const elementId = elementIdMap[type] || `${type}-results-grid`;
    const resultsGrid = document.getElementById(elementId);
    console.log(`Looking for element with ID: ${elementId}`);
    console.log(`Element found:`, resultsGrid);

    if (!resultsGrid) {
      console.error(
        `Results grid not found for type: ${type} (ID: ${elementId})`
      );
      console.log("Available elements with 'results-grid' in ID:");
      const allElements = document.querySelectorAll('[id*="results-grid"]');
      allElements.forEach((el) => console.log(`- ${el.id}`));
      return;
    }

    if (results.length === 0) {
      resultsGrid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon"><i class="fas fa-search"></i></div>
                    <div class="empty-title">No ${type} found</div>
                    <div class="empty-description">Try adjusting your search criteria.</div>
                </div>
            `;
      return;
    }

    switch (type) {
      case "flights":
        console.log(`Creating ${results.length} flight cards`);
        const flightCards = results.map((flight) => createFlightCard(flight));
        console.log("Flight cards HTML:", flightCards);
        resultsGrid.innerHTML = flightCards.join("");
        break;
      case "hotels":
        resultsGrid.innerHTML = results
          .map((hotel) => createHotelCard(hotel))
          .join("");
        break;
      case "activities":
        resultsGrid.innerHTML = results
          .map((activity) => createActivityCard(activity))
          .join("");
        break;
      case "packages":
        resultsGrid.innerHTML = results
          .map((package) => createPackageCard(package))
          .join("");
        break;
      case "agents":
        resultsGrid.innerHTML = results
          .map((agent) => createAgentCard(agent))
          .join("");
        break;
    }

    // Add booking event listeners
    addBookingEventListeners(type);
  }

  function createFlightCard(flight) {
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
      from = flight.from || flight.departure || "Unknown";
      to = flight.to || flight.destination || "Unknown";
      airline = flight.airline || "Unknown Airline";
      flightNumber = flight.flightNumber || flight.number || "XX1234";
      aircraft = flight.aircraft || "Boeing 737";
      departureTime = flight.departureTime || flight.time || "12:00 PM";
      departureDate = flight.departureDate || flight.date || "2024-06-15";
      duration = flight.duration || "3h 30m";
      price = flight.price || 299;
      currency = "USD"; // Default for mock data
      stops = flight.stops || 0;
      classType = flight.class || flight.class_type || "Economy";
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
                        <div class="flight-details">Flight ${flightNumber} • ${aircraft} • ${stops} stop${stops !== 1 ? "s" : ""}</div>
                    </div>
                </div>
                <div class="flight-times">
                    <div class="flight-time">${departureTime}</div>
                    <div class="flight-date">${departureDate}</div>
                </div>
                <div class="flight-duration">${duration}</div>
                <div class="flight-price">
                    <div class="price-amount">
                        <div class="primary-price">${getCurrencySymbol(
                          currency
                        )}${price}</div>
                        ${
                          currency !== "USD"
                            ? `<div class="secondary-price">$${(
                                price * getExchangeRate(currency, "USD")
                              ).toFixed(0)}</div>`
                            : ""
                        }
                        ${
                          currency !== "INR"
                            ? `<div class="secondary-price">₹${(
                                price * getExchangeRate(currency, "INR")
                              ).toFixed(0)}</div>`
                            : ""
                        }
                    </div>
                    <div class="price-per">per person</div>
                    <div class="price-class">${classType}</div>
                </div>
                <div class="flight-actions">
                    <button class="btn btn-primary btn-small" onclick="handleBooking('flights', '${flightId}')">
                        <i class="fas fa-plane"></i>
                        Book Flight
                    </button>
                </div>
            </div>
        `;
  }

  function createHotelCard(hotel) {
    console.log("Hotel card data:", hotel);

    // Handle both Amadeus API and mock data formats
    let name,
      location,
      rating,
      price,
      currency,
      amenities,
      description,
      distance,
      image,
      hotelId;

    if (hotel.price && hotel.price.total) {
      // Amadeus API format
      name = hotel.name || "Hotel";
      location =
        hotel.location?.address?.cityName ||
        hotel.location?.address?.countryCode ||
        "Unknown Location";
      rating = hotel.rating || 4.0;
      price = parseFloat(hotel.price.total);
      currency = hotel.price.currency || "USD";
      amenities = hotel.amenities || ["WiFi", "Pool"];
      description = hotel.room?.description || "Comfortable accommodation";
      distance = "City center";
      image =
        hotel.image_url ||
        "https://via.placeholder.com/200x150/f3f4f6/6b7280?text=Hotel";
      hotelId =
        hotel.id ||
        `hotel_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    } else {
      // Mock data format (fallback)
      name = hotel.name || "Hotel";
      location = hotel.location || "Unknown Location";
      rating = hotel.rating || 4.0;
      price = hotel.price || 150;
      currency = "USD"; // Default for mock data
      amenities = hotel.amenities || ["WiFi", "Pool"];
      description = hotel.description || "Comfortable accommodation";
      distance = hotel.distance || "0.5 km from center";
      image =
        hotel.image ||
        "https://via.placeholder.com/200x150/f3f4f6/6b7280?text=Hotel";
      hotelId =
        hotel.id ||
        `hotel_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    return `
            <div class="hotel-card">
                <img src="${image}" alt="${name}" class="hotel-image" onerror="this.src='https://via.placeholder.com/200x150/f3f4f6/6b7280?text=Hotel'">
                <div class="hotel-info">
                    <div>
                        <div class="hotel-name">${name}</div>
                        <div class="hotel-location">
                            <i class="fas fa-map-marker-alt"></i> ${location}
                        </div>
                        <div class="hotel-description">${description}</div>
                        <div class="hotel-distance">
                            <i class="fas fa-location-arrow"></i> ${distance}
                        </div>
                        <div class="hotel-amenities">
                            ${amenities
                              .map(
                                (amenity) => `
                                <span class="amenity">
                                    <i class="fas fa-${getAmenityIcon(
                                      amenity
                                    )}"></i> ${amenity}
                                </span>
                            `
                              )
                              .join("")}
                        </div>
                    </div>
                    <div class="hotel-rating">
                        <div class="rating-stars">${"★".repeat(
                          Math.floor(rating)
                        )}${"☆".repeat(5 - Math.floor(rating))}</div>
                        <div class="rating-score">${rating.toFixed(1)}/5</div>
                    </div>
                </div>
                <div class="hotel-price">
                    <div class="price-amount">
                        <div class="primary-price">${getCurrencySymbol(
                          currency
                        )}${price}</div>
                        ${
                          currency !== "USD"
                            ? `<div class="secondary-price">$${(
                                price * getExchangeRate(currency, "USD")
                              ).toFixed(0)}</div>`
                            : ""
                        }
                        ${
                          currency !== "INR"
                            ? `<div class="secondary-price">₹${(
                                price * getExchangeRate(currency, "INR")
                              ).toFixed(0)}</div>`
                            : ""
                        }
                    </div>
                    <div class="price-per">per night</div>
                </div>
                <div class="hotel-actions">
                    <button class="btn btn-primary btn-small" onclick="handleBooking('hotels', '${hotelId}')">
                        <i class="fas fa-bed"></i>
                        Book Hotel
                    </button>
                </div>
            </div>
        `;
  }

  function getCurrencySymbol(currencyCode) {
    const currencySymbols = {
      USD: "$",
      EUR: "€",
      GBP: "£",
      INR: "₹",
      JPY: "¥",
      CAD: "C$",
      AUD: "A$",
      CHF: "CHF",
      CNY: "¥",
      KRW: "₩",
      SGD: "S$",
      HKD: "HK$",
      AED: "AED",
      SAR: "SAR",
      THB: "฿",
      MYR: "RM",
      IDR: "Rp",
      PHP: "₱",
      VND: "₫",
      BRL: "R$",
      MXN: "MX$",
      ARS: "AR$",
      CLP: "CL$",
      PEN: "S/",
      COP: "CO$",
      UYU: "UY$",
      PYG: "₲",
      BOB: "Bs",
      EGP: "E£",
      ZAR: "R",
      NGN: "₦",
      KES: "KSh",
      GHS: "GH₵",
      MAD: "MAD",
      TND: "TND",
      RUB: "₽",
      TRY: "₺",
      PLN: "zł",
      CZK: "Kč",
      HUF: "Ft",
      RON: "lei",
      BGN: "лв",
      HRK: "kn",
      SEK: "kr",
      NOK: "kr",
      DKK: "kr",
      ISK: "kr",
    };
    return currencySymbols[currencyCode] || currencyCode;
  }

  function getExchangeRate(fromCurrency, toCurrency) {
    // Approximate exchange rates (you can update these or use a real API)
    const exchangeRates = {
      USD: {
        INR: 83.5, // 1 USD = 83.5 INR
        EUR: 0.92,
        GBP: 0.79,
        JPY: 150.5,
        CAD: 1.35,
        AUD: 1.52,
        CHF: 0.87,
        CNY: 7.23,
        KRW: 1330,
        SGD: 1.34,
        HKD: 7.82,
        AED: 3.67,
        SAR: 3.75,
        THB: 35.8,
        MYR: 4.72,
        IDR: 15750,
        PHP: 56.2,
        VND: 24500,
        BRL: 4.95,
        MXN: 17.2,
        ARS: 850,
        CLP: 950,
        PEN: 3.72,
        COP: 3950,
        UYU: 39.5,
        PYG: 7300,
        BOB: 6.92,
        EGP: 31.2,
        ZAR: 18.8,
        NGN: 1600,
        KES: 160,
        GHS: 12.5,
        MAD: 10.2,
        TND: 3.12,
        RUB: 92.5,
        TRY: 31.2,
        PLN: 3.95,
        CZK: 22.8,
        HUF: 350,
        RON: 4.58,
        BGN: 1.79,
        HRK: 6.95,
        SEK: 10.4,
        NOK: 10.6,
        DKK: 6.88,
        ISK: 138,
      },
      INR: {
        USD: 0.012, // 1 INR = 0.012 USD
        EUR: 0.011,
        GBP: 0.0095,
        JPY: 1.8,
        CAD: 0.016,
        AUD: 0.018,
        CHF: 0.0104,
        CNY: 0.087,
        KRW: 15.9,
        SGD: 0.016,
        HKD: 0.094,
        AED: 0.044,
        SAR: 0.045,
        THB: 0.43,
        MYR: 0.057,
        IDR: 189,
        PHP: 0.67,
        VND: 293,
        BRL: 0.059,
        MXN: 0.206,
        ARS: 10.2,
        CLP: 11.4,
        PEN: 0.045,
        COP: 47.3,
        UYU: 0.473,
        PYG: 87.4,
        BOB: 0.083,
        EGP: 0.374,
        ZAR: 0.225,
        NGN: 19.2,
        KES: 1.92,
        GHS: 0.15,
        MAD: 0.122,
        TND: 0.037,
        RUB: 1.11,
        TRY: 0.374,
        PLN: 0.047,
        CZK: 0.273,
        HUF: 4.19,
        RON: 0.055,
        BGN: 0.021,
        HRK: 0.083,
        SEK: 0.125,
        NOK: 0.127,
        DKK: 0.082,
        ISK: 1.65,
      },
    };

    // If converting from USD to another currency
    if (fromCurrency === "USD" && exchangeRates.USD[toCurrency]) {
      return exchangeRates.USD[toCurrency];
    }

    // If converting from INR to another currency
    if (fromCurrency === "INR" && exchangeRates.INR[toCurrency]) {
      return exchangeRates.INR[toCurrency];
    }

    // If converting to USD from another currency
    if (
      toCurrency === "USD" &&
      exchangeRates[fromCurrency] &&
      exchangeRates[fromCurrency].USD
    ) {
      return exchangeRates[fromCurrency].USD;
    }

    // If converting to INR from another currency
    if (
      toCurrency === "INR" &&
      exchangeRates[fromCurrency] &&
      exchangeRates[fromCurrency].INR
    ) {
      return exchangeRates[fromCurrency].INR;
    }

    // Default fallback
    return 1;
  }

  function getAmenityIcon(amenity) {
    const iconMap = {
      WiFi: "wifi",
      Pool: "swimming-pool",
      Spa: "spa",
      Gym: "dumbbell",
      Restaurant: "utensils",
      Bar: "glass-martini-alt",
      Parking: "car",
      "Room Service": "concierge-bell",
      "Air Conditioning": "snowflake",
      "Free Breakfast": "coffee",
    };
    return iconMap[amenity] || "check";
  }

  function createActivityCard(activity) {
    // Handle both API and mock data formats
    const name = activity.name || "Activity";
    const category = activity.category || "Adventure";
    const description = activity.description || "Exciting activity";
    const duration = activity.duration || "3 hours";
    const rating = activity.rating || 4.0;
    const price = activity.price || 50;
    const location = activity.location || "Unknown Location";
    const image =
      activity.image ||
      "https://via.placeholder.com/200x150/f3f4f6/6b7280?text=Activity";

    return `
            <div class="activity-card">
                <img src="${image}" alt="${name}" class="activity-image" onerror="this.src='https://via.placeholder.com/200x150/f3f4f6/6b7280?text=Activity'">
                <div class="activity-info">
                    <div>
                        <div class="activity-name">${name}</div>
                        <div class="activity-category">${category}</div>
                        <div class="activity-location">
                            <i class="fas fa-map-marker-alt"></i> ${location}
                        </div>
                        <div class="activity-description">${description}</div>
                        <div class="activity-details">
                            <span class="activity-detail">
                                <i class="fas fa-clock"></i> ${duration}
                            </span>
                            <span class="activity-detail">
                                <i class="fas fa-star"></i> ${rating.toFixed(
                                  1
                                )}/5
                            </span>
                        </div>
                    </div>
                </div>
                <div class="activity-price">
                    <div class="price-amount">$${price}</div>
                    <div class="price-per">per person</div>
                </div>
                <div class="activity-actions">
                    <button class="btn btn-primary btn-small" onclick="handleBooking('activities', '${
                      activity.id
                    }')">
                        <i class="fas fa-hiking"></i>
                        Book Activity
                    </button>
                </div>
            </div>
        `;
  }

  function createPackageCard(package) {
    // Handle both API and mock data formats
    const name = package.name || "Travel Package";
    const from = package.from || "Unknown";
    const to = package.to || "Unknown";
    const duration = package.duration || "7 days";
    const price = package.price || 800;
    const description = package.description || "Complete travel experience";
    const inclusions = package.inclusions ||
      package.includes || ["Flight", "Hotel", "Transfers"];
    const image =
      package.image ||
      "https://via.placeholder.com/250x180/f3f4f6/6b7280?text=Package";

    return `
            <div class="package-card">
                <img src="${image}" alt="${name}" class="package-image" onerror="this.src='https://via.placeholder.com/250x180/f3f4f6/6b7280?text=Package'">
                <div class="package-info">
                    <div>
                        <div class="package-name">${name}</div>
                        <div class="package-route">
                            <i class="fas fa-plane"></i> ${from} → ${to}
                        </div>
                        <div class="package-description">${description}</div>
                        <div class="package-duration">
                            <i class="fas fa-calendar"></i> ${duration}
                        </div>
                        <div class="package-includes">
                            ${inclusions
                              .map(
                                (item) => `
                                <span class="package-include">
                                    <i class="fas fa-check"></i> ${item}
                                </span>
                            `
                              )
                              .join("")}
                        </div>
                    </div>
                </div>
                <div class="package-price">
                    <div class="price-amount">$${price}</div>
                    <div class="price-per">per person</div>
                </div>
                <div class="package-actions">
                    <button class="btn btn-primary btn-small" onclick="handleBooking('packages', '${
                      package.id
                    }')">
                        <i class="fas fa-suitcase"></i>
                        Book Package
                    </button>
                </div>
            </div>
        `;
  }

  function createAgentCard(agent) {
    return `
            <div class="agent-card">
                <img src="${agent.avatar}" alt="${agent.name}" class="agent-avatar" onerror="this.src='https://via.placeholder.com/120x120/f3f4f6/6b7280?text=Agent'">
                <div class="agent-info">
                    <div>
                        <div class="agent-name">${agent.name}</div>
                        <div class="agent-specialty">${agent.specialty}</div>
                        <div class="agent-description">${agent.description}</div>
                        <div class="agent-stats">
                            <span class="agent-stat">
                                <i class="fas fa-star"></i> ${agent.rating}/5
                            </span>
                            <span class="agent-stat">
                                <i class="fas fa-users"></i> ${agent.clients} clients
                            </span>
                            <span class="agent-stat">
                                <i class="fas fa-globe"></i> ${agent.experience} years
                            </span>
                        </div>
                    </div>
                </div>
                <div class="agent-actions">
                    <button class="contact-agent-btn" data-agent-id="${agent.id}">
                        <i class="fas fa-phone"></i> Contact
                    </button>
                    <button class="view-profile-btn" data-agent-id="${agent.id}">
                        <i class="fas fa-user"></i> View Profile
                    </button>
                </div>
            </div>
        `;
  }

  function addBookingEventListeners(type) {
    const buttons = document.querySelectorAll(`[data-${type}-id]`);
    buttons.forEach((button) => {
      button.addEventListener("click", (e) => {
        const id = e.target.dataset[`${type}Id`];
        handleBooking(type, id);
      });
    });
  }

  function handleBooking(type, id) {
    showBookingModal(type, id);
  }

  // Enhanced booking modal with form validation and submission

  function showBookingModal(type, id) {
    const modal = document.createElement("div");
    modal.className = "booking-modal";
    modal.innerHTML = `
            <div class="booking-modal-content">
                <div class="booking-modal-header">
                    <h3>Book ${
                      type.charAt(0).toUpperCase() + type.slice(1)
                    }</h3>
                    <button class="modal-close" onclick="this.closest('.booking-modal').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="booking-modal-body">
                    <p>Redirecting to booking partner...</p>
                    <div class="loading-spinner"></div>
                </div>
            </div>
        `;

    document.body.appendChild(modal);

    setTimeout(() => {
      showToast(`Redirecting to ${type} booking...`, "success");
      modal.remove();
    }, 2000);
  }

  // Submit booking function
  async function submitBooking(type, id, form, modal) {
    const submitButton = form.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;

    try {
      // Show loading state
      submitButton.textContent = "Processing...";
      submitButton.disabled = true;

      // Collect form data
      const formData = {
        booking_type: type,
        item_id: id,
        customer_name: form.querySelector("#customer-name").value.trim(),
        customer_email: form.querySelector("#customer-email").value.trim(),
        customer_phone:
          form.querySelector("#customer-phone").value.trim() || null,
        travel_date: form.querySelector("#travel-date").value,
        return_date: form.querySelector("#return-date").value || null,
        passengers: parseInt(form.querySelector("#passengers").value),
        special_requests:
          form.querySelector("#special-requests").value.trim() || null,
        total_price: getItemPrice(type, id), // Get price from the item
        currency: "USD",
      };

      // Validate form data
      if (
        !formData.customer_name ||
        !formData.customer_email ||
        !formData.travel_date
      ) {
        throw new Error("Please fill in all required fields");
      }

      // Validate email format
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(formData.customer_email)) {
        throw new Error("Please enter a valid email address");
      }

      // Validate travel date
      const travelDate = new Date(formData.travel_date);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      if (travelDate < today) {
        throw new Error("Travel date must be in the future");
      }

      // Submit booking to API
      const response = await fetch("http://localhost:8000/api/book", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(
          errorData.detail || "Booking failed. Please try again."
        );
      }

      const result = await response.json();

      // Show success message
      showToast("Booking confirmed successfully!", "success");

      // Show success modal
      showBookingSuccess(result);

      // Close the booking modal
      modal.remove();
    } catch (error) {
      console.error("Booking error:", error);
      showToast(error.message || "Booking failed. Please try again.", "error");
    } finally {
      // Reset button state
      submitButton.textContent = originalText;
      submitButton.disabled = false;
    }
  }

  // Get item price based on type and id
  function getItemPrice(type, id) {
    // Mock prices - in a real app, you'd get this from the item data
    const priceMap = {
      flights: { f1: 899, f2: 745, f3: 650 },
      hotels: { h1: 350, h2: 850, h3: 200 },
      activities: { a1: 89, a2: 125, a3: 75 },
      packages: { p1: 1299, p2: 899, p3: 1500 },
      agents: { ag1: 50, ag2: 75, ag3: 60 },
    };

    return priceMap[type]?.[id] || 100; // Default price
  }

  // Show booking success modal
  function showBookingSuccess(result) {
    const modal = document.createElement("div");
    modal.className = "success-modal";
    modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        `;

    const modalContent = document.createElement("div");
    modalContent.className = "success-modal-content";
    modalContent.style.cssText = `
            background: white;
            border-radius: 16px;
            padding: 32px;
            max-width: 500px;
            width: 90%;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        `;

    modalContent.innerHTML = `
            <div class="success-icon" style="
                width: 80px;
                height: 80px;
                background: #4CAF50;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 24px;
                font-size: 40px;
                color: white;
            ">
                <i class="fas fa-check"></i>
            </div>
            
            <h3 style="margin: 0 0 16px; color: #1a1a1a; font-size: 24px;">Booking Confirmed!</h3>
            
            <div style="background: #f8f9fa; border-radius: 8px; padding: 20px; margin: 20px 0;">
                <p style="margin: 0 0 8px; font-weight: 500; color: #333;">Booking ID:</p>
                <p style="margin: 0; font-size: 18px; font-weight: 600; color: #667eea; font-family: monospace;">${
                  result.booking_id
                }</p>
            </div>
            
            <p style="margin: 0 0 20px; color: #666; line-height: 1.5;">
                Your booking has been confirmed successfully! We've sent a confirmation email to <strong>${
                  result.booking.customer_email
                }</strong>.
            </p>
            
            <div style="text-align: left; background: #f8f9fa; border-radius: 8px; padding: 16px; margin: 20px 0;">
                <h4 style="margin: 0 0 12px; color: #333;">Next Steps:</h4>
                <ul style="margin: 0; padding-left: 20px; color: #666;">
                    ${result.next_steps
                      .map((step) => `<li>${step}</li>`)
                      .join("")}
                </ul>
            </div>
            
            <div style="display: flex; gap: 12px; margin-top: 24px;">
                <button onclick="window.location.href='booking.html'" style="
                    flex: 1;
                    padding: 14px 24px;
                    border: 2px solid #e1e5e9;
                    border-radius: 8px;
                    background: white;
                    color: #666;
                    font-size: 16px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.3s;
                ">Book Another</button>
                <button onclick="window.location.href='index.html'" style="
                    flex: 1;
                    padding: 14px 24px;
                    border: none;
                    border-radius: 8px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    font-size: 16px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.3s;
                ">Go Home</button>
            </div>
        `;

    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    // Auto-close after 10 seconds
    setTimeout(() => {
      if (modal.parentNode) {
        modal.remove();
      }
    }, 10000);
  }

  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.innerHTML = `
            <div class="toast-icon">
                <i class="fas fa-${
                  type === "success"
                    ? "check-circle"
                    : type === "error"
                    ? "exclamation-circle"
                    : "info-circle"
                }"></i>
            </div>
            <div class="toast-message">${message}</div>
            <button class="toast-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;

    const container = document.getElementById("toast-container");
    if (container) {
      container.appendChild(toast);
      setTimeout(() => {
        if (toast.parentElement) {
          toast.remove();
        }
      }, 5000);
    }
  }

  function getMockResults(type) {
    switch (type) {
      case "flights":
        return getMockFlights();
      case "hotels":
        return getMockHotels();
      case "activities":
        return getMockActivities();
      case "packages":
        return getMockPackages();
      case "agents":
        return getMockAgents();
      default:
        return [];
    }
  }

  function getMockFlights() {
    return [
      {
        id: "f1",
        from: "New York",
        to: "Paris",
        airline: "Air France",
        flightNumber: "AF123",
        aircraft: "Boeing 777",
        departureTime: "10:30 AM",
        departureDate: "Dec 15, 2024",
        duration: "7h 45m",
        price: 899,
      },
      {
        id: "f2",
        from: "New York",
        to: "Paris",
        airline: "Delta Airlines",
        flightNumber: "DL456",
        aircraft: "Airbus A350",
        departureTime: "2:15 PM",
        departureDate: "Dec 15, 2024",
        duration: "8h 20m",
        price: 745,
      },
    ];
  }

  function getMockHotels() {
    return [
      {
        id: "h1",
        name: "Le Grand Hotel Paris",
        location: "Champs-Élysées, Paris",
        image:
          "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=400",
        price: 350,
        rating: 4.8,
        amenities: [
          { name: "WiFi", icon: "wifi" },
          { name: "Pool", icon: "swimming-pool" },
          { name: "Spa", icon: "spa" },
          { name: "Restaurant", icon: "utensils" },
        ],
      },
      {
        id: "h2",
        name: "Hotel Ritz Paris",
        location: "Place Vendôme, Paris",
        image:
          "https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=400",
        price: 850,
        rating: 4.9,
        amenities: [
          { name: "WiFi", icon: "wifi" },
          { name: "Gym", icon: "dumbbell" },
          { name: "Spa", icon: "spa" },
          { name: "Bar", icon: "glass-martini" },
        ],
      },
    ];
  }

  function getMockActivities() {
    return [
      {
        id: "a1",
        name: "Eiffel Tower Skip-the-Line Tour",
        category: "Culture",
        description:
          "Skip the long lines and enjoy priority access to the iconic Eiffel Tower.",
        image:
          "https://images.unsplash.com/photo-1511739001486-6bfe10ce785f?w=400",
        price: 89,
        duration: "2 hours",
        maxParticipants: 15,
        rating: 4.6,
      },
      {
        id: "a2",
        name: "Seine River Dinner Cruise",
        category: "Food",
        description:
          "Enjoy a romantic dinner cruise along the Seine River with stunning views.",
        image:
          "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=400",
        price: 125,
        duration: "3 hours",
        maxParticipants: 50,
        rating: 4.8,
      },
    ];
  }

  function getMockPackages() {
    return [
      {
        id: "p1",
        name: "Paris Romantic Getaway",
        type: "Romantic",
        description:
          "Perfect for couples, this package includes luxury hotel and romantic dinner.",
        image:
          "https://images.unsplash.com/photo-1502602898534-47d22c0d8064?w=400",
        price: 1299,
        duration: "5 days, 4 nights",
        includes: [
          "Luxury Hotel",
          "Airport Transfer",
          "Romantic Dinner",
          "Private Tours",
        ],
      },
      {
        id: "p2",
        name: "Paris Family Adventure",
        type: "Family",
        description: "Family-friendly package with activities for all ages.",
        image:
          "https://images.unsplash.com/photo-1523050854058-8df90110c9e1?w=400",
        price: 899,
        duration: "6 days, 5 nights",
        includes: [
          "Family Hotel",
          "Airport Transfer",
          "Family Tours",
          "Museum Passes",
        ],
      },
    ];
  }

  function getMockAgents() {
    return [
      {
        id: "ag1",
        name: "Marie Dubois",
        specialty: "Luxury Travel",
        description:
          "Specializing in luxury European travel with over 15 years of experience.",
        avatar:
          "https://images.unsplash.com/photo-1494790108755-2616b612b786?w=120",
        rating: 4.9,
        clients: 250,
        experience: 15,
      },
      {
        id: "ag2",
        name: "Jean-Pierre Martin",
        specialty: "Adventure Travel",
        description:
          "Expert in adventure and outdoor travel experiences across Europe.",
        avatar:
          "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=120",
        rating: 4.7,
        clients: 180,
        experience: 12,
      },
    ];
  }
});

// Add booking modal styles
const modalStyles = `
<style>
.booking-modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.booking-modal-content {
    background: white;
    border-radius: 1rem;
    padding: 2rem;
    max-width: 500px;
    width: 90%;
    text-align: center;
}

.booking-modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
}

.booking-modal-header h3 {
    margin: 0;
    color: #1f2937;
}

.modal-close {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: #6b7280;
}

.modal-close:hover {
    color: #374151;
}

.booking-modal-body {
    color: #6b7280;
}

.booking-modal-body .loading-spinner {
    margin: 1rem auto;
}
</style>
`;

document.head.insertAdjacentHTML("beforeend", modalStyles);
