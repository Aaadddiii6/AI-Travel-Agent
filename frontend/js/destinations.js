// Destinations Page JavaScript
class DestinationsPage {
  constructor() {
    this.api = new APIService();
    this.destinations = [];
    this.filteredDestinations = [];
    this.continents = [];
    this.uploadedPhotoUrl = null;
    this.currentFilter = "all";
    this.currentSearch = "";
    this.init();
  }

  init() {
    this.loadUploadedPhoto();
    this.loadContinents();
    this.loadDestinations();
    this.setupSearchFilter();
    this.setupEventListeners();
    this.checkBackendStatus();
  }

  async checkBackendStatus() {
    const backendAvailable = await this.api.checkBackendHealth();
    if (!backendAvailable) {
      uiComponents.showToast(
        "Backend server is not available. Using demo data.",
        "warning"
      );
    }
  }

  loadUploadedPhoto() {
    // Load uploaded photo URL from session storage (from upload page)
    const savedPhotoUrl = sessionStorage.getItem("uploadedPhotoUrl");
    console.log("Loading saved photo URL:", savedPhotoUrl); // Debug log
    if (savedPhotoUrl) {
      this.uploadedPhotoUrl = savedPhotoUrl;
      console.log("Photo URL loaded:", this.uploadedPhotoUrl); // Debug log
      this.showUploadedPhotoInfo();
    } else {
      console.log("No saved photo URL found"); // Debug log
    }
  }

  showUploadedPhotoInfo() {
    if (!this.uploadedPhotoUrl) return;

    const photoInfo = document.createElement("div");
    photoInfo.className = "upload-info";
    photoInfo.innerHTML = `
            <div class="info-icon">📸</div>
            <div class="info-title">Photo Ready for Matching</div>
            <div class="info-content">
                <p>Your uploaded photo is ready to be matched with destinations!</p>
                <img src="${this.uploadedPhotoUrl}" alt="Uploaded photo" style="width: 100px; height: 100px; object-fit: cover; border-radius: 8px; margin: 10px 0;">
                <button class="btn btn-secondary" onclick="destinationsPage.clearUploadedPhoto()">Remove Photo</button>
            </div>
        `;

    const header = document.querySelector(".destinations-header");
    if (header) {
      header.appendChild(photoInfo);
    }
  }

  clearUploadedPhoto() {
    this.uploadedPhotoUrl = null;
    sessionStorage.removeItem("uploadedPhotoUrl");
    const photoInfo = document.querySelector(".upload-info");
    if (photoInfo) {
      photoInfo.remove();
    }
    uiComponents.showToast("Photo removed", "success");
  }

  async loadContinents() {
    try {
      const backendAvailable = await this.api.checkBackendHealth();

      if (backendAvailable) {
        const response = await this.api.getContinents();
        this.continents =
          response && Array.isArray(response.data) ? response.data : [];
        if (!Array.isArray(this.continents)) {
          this.continents = [];
          throw new Error("Failed to load continents");
        }
      } else {
        // Mock continents for demo
        this.continents = [
          { name: "Europe", count: 2 },
          { name: "Asia", count: 1 },
          { name: "North America", count: 1 },
          { name: "Africa", count: 1 },
          { name: "Oceania", count: 1 },
        ];
      }

      this.populateContinentFilter();
    } catch (error) {
      console.error("Failed to load continents:", error);
      uiComponents.showToast("Failed to load continents", "error");
    }
  }

  populateContinentFilter() {
    const filterSelect = document.querySelector(".filter-select");
    if (filterSelect) {
      // Clear existing options except "All"
      filterSelect.innerHTML = '<option value="all">All Continents</option>';

      // Defensive: ensure this.continents is always an array
      let continentsArr = Array.isArray(this.continents) ? this.continents : [];
      if (!Array.isArray(this.continents)) {
        console.error(
          "populateContinentFilter: this.continents is not an array",
          this.continents
        );
      }
      continentsArr.forEach((continent) => {
        const option = document.createElement("option");
        option.value = continent.name;
        option.textContent = `${continent.name} (${continent.count})`;
        filterSelect.appendChild(option);
      });
    }
  }

  async loadDestinations() {
    const loadingState = document.querySelector(".loading-state");
    const destinationsGrid = document.querySelector(".destinations-grid");
    const emptyState = document.querySelector(".empty-state");

    if (loadingState) loadingState.style.display = "flex";
    if (destinationsGrid) destinationsGrid.style.display = "none";
    if (emptyState) emptyState.style.display = "none";

    try {
      const backendAvailable = await this.api.checkBackendHealth();
      let response = null;

      if (backendAvailable) {
        // Use real API
        response = await this.api.getDestinations();
        if (response && response.success && response.data) {
          this.destinations = response.data.map((dest) => ({
            ...dest,
            rating: dest.rating || 4.5,
            price: dest.price || this.getPriceFromRating(dest.rating || 4.5),
            bestTime:
              dest.bestTime || this.getBestTimeFromContinent(dest.continent),
            highlights:
              dest.highlights ||
              this.getHighlightsFromContinent(dest.continent),
          }));
        } else {
          throw new Error("Failed to load destinations from API");
        }
      } else {
        // Use mock data
        this.destinations = this.api.getMockDestinations();
      }

      this.filteredDestinations = [...this.destinations];
      this.renderDestinations();
      this.updateResultsSummary();

      // Show generation info if from OpenAI
      if (response && response.source === "openai") {
        const generationInfo = document.querySelector("#generation-info");
        const generationText = document.querySelector("#generation-text");
        if (generationInfo && generationText) {
          generationText.textContent = `AI Generated - ${new Date().toLocaleTimeString()}`;
          generationInfo.style.display = "flex";
        }
      }
    } catch (error) {
      console.error("Failed to load destinations:", error);
      uiComponents.showToast(
        "Failed to load destinations. Please try again.",
        "error"
      );
      this.showEmptyState();
    } finally {
      if (loadingState) loadingState.style.display = "none";
    }
  }

  getPriceFromRating(rating) {
    if (rating >= 4.7) return "$$$";
    if (rating >= 4.3) return "$$";
    return "$";
  }

  getBestTimeFromContinent(continent) {
    const bestTimes = {
      Europe: "May-September",
      Asia: "March-May, October-November",
      "North America": "June-September",
      Africa: "March-May, September-November",
      Oceania: "December-February",
    };
    return bestTimes[continent] || "Year-round";
  }

  getHighlightsFromContinent(continent) {
    const highlights = {
      Europe: [
        "Cultural Sites",
        "Historic Architecture",
        "Local Cuisine",
        "Scenic Views",
      ],
      Asia: [
        "Temples",
        "Traditional Culture",
        "Natural Beauty",
        "Local Markets",
      ],
      "North America": [
        "Outdoor Activities",
        "Wildlife",
        "Scenic Landscapes",
        "Adventure Sports",
      ],
      Africa: [
        "Wildlife Safaris",
        "Cultural Experiences",
        "Desert Landscapes",
        "Local Markets",
      ],
      Oceania: [
        "Adventure Sports",
        "Natural Beauty",
        "Indigenous Culture",
        "Beach Activities",
      ],
    };
    return (
      highlights[continent] || [
        "Local Attractions",
        "Cultural Sites",
        "Natural Beauty",
        "Local Cuisine",
      ]
    );
  }

  setupSearchFilter() {
    const searchInput = document.querySelector(".search-input");
    const filterSelect = document.querySelector(".filter-select");
    const refreshBtn = document.querySelector("#refresh-destinations");

    if (searchInput) {
      // Enhanced search with autocomplete
      let searchTimeout;
      searchInput.addEventListener("input", (e) => {
        this.currentSearch = e.target.value;

        // Clear previous timeout
        clearTimeout(searchTimeout);

        // Show suggestions if query is long enough
        if (this.currentSearch.length >= 2) {
          searchTimeout = setTimeout(() => {
            this.showSearchSuggestions(this.currentSearch);
          }, 300);
        } else {
          this.hideSearchSuggestions();
        }

        this.filterDestinations();
      });

      // Handle keyboard navigation
      searchInput.addEventListener("keydown", (e) => {
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
          e.preventDefault();
          this.navigateSuggestions(e.key);
        } else if (e.key === "Enter") {
          e.preventDefault();
          this.selectCurrentSuggestion();
        } else if (e.key === "Escape") {
          this.hideSearchSuggestions();
        }
      });

      // Hide suggestions when clicking outside
      document.addEventListener("click", (e) => {
        if (
          !searchInput.contains(e.target) &&
          !e.target.closest(".search-suggestions")
        ) {
          this.hideSearchSuggestions();
        }
      });
    }

    if (filterSelect) {
      filterSelect.addEventListener("change", (e) => {
        this.currentFilter = e.target.value;
        this.filterDestinations();
      });
    }

    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => {
        this.refreshDestinations();
      });
    }
  }

  async showSearchSuggestions(query) {
    try {
      const response = await this.api.getDestinationSuggestions(query);
      if (response.suggestions && response.suggestions.length > 0) {
        this.renderSearchSuggestions(response.suggestions, query);
      } else {
        this.hideSearchSuggestions();
      }
    } catch (error) {
      console.error("Failed to get suggestions:", error);
      this.hideSearchSuggestions();
    }
  }

  renderSearchSuggestions(suggestions, query) {
    const suggestionsContainer = document.querySelector("#search-suggestions");
    if (!suggestionsContainer) return;

    suggestionsContainer.innerHTML = "";

    suggestions.forEach((suggestion, index) => {
      const item = document.createElement("div");
      item.className = "search-suggestion-item";
      item.dataset.index = index;
      item.dataset.value = suggestion;

      // Highlight matching text
      const highlightedText = this.highlightText(suggestion, query);

      item.innerHTML = `
                <i class="fas fa-map-marker-alt search-suggestion-icon"></i>
                <span class="search-suggestion-text">${highlightedText}</span>
            `;

      item.addEventListener("click", () => {
        this.selectSuggestion(suggestion);
      });

      item.addEventListener("mouseenter", () => {
        this.setActiveSuggestion(index);
      });

      suggestionsContainer.appendChild(item);
    });

    suggestionsContainer.style.display = "block";
    this.currentSuggestions = suggestions;
    this.activeSuggestionIndex = -1;
  }

  highlightText(text, query) {
    if (!query) return text;
    const regex = new RegExp(`(${query})`, "gi");
    return text.replace(
      regex,
      '<span class="search-suggestion-highlight">$1</span>'
    );
  }

  hideSearchSuggestions() {
    const suggestionsContainer = document.querySelector("#search-suggestions");
    if (suggestionsContainer) {
      suggestionsContainer.style.display = "none";
    }
    this.currentSuggestions = null;
    this.activeSuggestionIndex = -1;
  }

  navigateSuggestions(direction) {
    if (!this.currentSuggestions) return;

    const items = document.querySelectorAll(".search-suggestion-item");
    if (items.length === 0) return;

    // Remove previous active state
    items.forEach((item) => item.classList.remove("active"));

    if (direction === "ArrowDown") {
      this.activeSuggestionIndex = Math.min(
        this.activeSuggestionIndex + 1,
        items.length - 1
      );
    } else {
      this.activeSuggestionIndex = Math.max(this.activeSuggestionIndex - 1, -1);
    }

    // Add active state to current item
    if (this.activeSuggestionIndex >= 0) {
      items[this.activeSuggestionIndex].classList.add("active");
    }
  }

  setActiveSuggestion(index) {
    const items = document.querySelectorAll(".search-suggestion-item");
    items.forEach((item) => item.classList.remove("active"));

    if (index >= 0 && items[index]) {
      items[index].classList.add("active");
      this.activeSuggestionIndex = index;
    }
  }

  selectCurrentSuggestion() {
    if (this.activeSuggestionIndex >= 0 && this.currentSuggestions) {
      this.selectSuggestion(
        this.currentSuggestions[this.activeSuggestionIndex]
      );
    }
  }

  selectSuggestion(suggestion) {
    const searchInput = document.querySelector(".search-input");
    if (searchInput) {
      searchInput.value = suggestion;
      this.currentSearch = suggestion;
      this.hideSearchSuggestions();
      this.filterDestinations();
    }
  }

  async refreshDestinations() {
    const refreshBtn = document.querySelector("#refresh-destinations");
    if (refreshBtn) {
      refreshBtn.classList.add("loading");
      refreshBtn.disabled = true;
    }

    try {
      uiComponents.showToast("Generating new destinations...", "info");
      await this.loadDestinations();
      uiComponents.showToast("New destinations generated!", "success");

      // Show generation info
      const generationInfo = document.querySelector("#generation-info");
      const generationText = document.querySelector("#generation-text");
      if (generationInfo && generationText) {
        generationText.textContent = `AI Generated - ${new Date().toLocaleTimeString()}`;
        generationInfo.style.display = "flex";
      }
    } catch (error) {
      console.error("Failed to refresh destinations:", error);
      uiComponents.showToast("Failed to generate new destinations", "error");
    } finally {
      if (refreshBtn) {
        refreshBtn.classList.remove("loading");
        refreshBtn.disabled = false;
      }
    }
  }

  filterDestinations() {
    let filtered = [...this.destinations];

    // Apply search filter
    if (this.currentSearch) {
      const searchTerm = this.currentSearch.toLowerCase();
      filtered = filtered.filter(
        (dest) =>
          dest.name.toLowerCase().includes(searchTerm) ||
          dest.country.toLowerCase().includes(searchTerm) ||
          dest.city.toLowerCase().includes(searchTerm) ||
          dest.description.toLowerCase().includes(searchTerm)
      );
    }

    // Apply continent filter
    if (this.currentFilter && this.currentFilter !== "all") {
      filtered = filtered.filter(
        (dest) =>
          dest.continent.toLowerCase() === this.currentFilter.toLowerCase()
      );
    }

    this.filteredDestinations = filtered;
    this.renderDestinations();
    this.updateResultsSummary();
  }

  updateResultsSummary() {
    const resultsCount = document.querySelector("#results-count");
    if (resultsCount) {
      resultsCount.textContent = `${this.filteredDestinations.length} destinations found`;
    }
  }

  setupEventListeners() {
    this.setupBackToUpload();
  }

  setupBackToUpload() {
    const backButton = document.querySelector(".btn-warning");
    if (backButton) {
      backButton.addEventListener("click", () => {
        window.location.href = "upload.html";
      });
    }
  }

  renderDestinations() {
    const destinationsGrid = document.querySelector(".destinations-grid");
    const emptyState = document.querySelector(".empty-state");

    if (!destinationsGrid) return;

    if (this.filteredDestinations.length === 0) {
      destinationsGrid.style.display = "none";
      if (emptyState) {
        emptyState.style.display = "block";
        const emptyDescription = document.querySelector("#empty-description");
        if (emptyDescription) {
          emptyDescription.textContent =
            this.currentSearch || this.currentFilter !== "all"
              ? "No destinations match your search criteria. Try adjusting your filters."
              : "No destinations available at the moment. Please check back later.";
        }
      }
      return;
    }

    destinationsGrid.style.display = "grid";
    if (emptyState) emptyState.style.display = "none";

    destinationsGrid.innerHTML = this.filteredDestinations
      .map((dest) => this.createDestinationCard(dest))
      .join("");

    this.setupCardInteractions();
  }

  createDestinationCard(destination) {
    const stars = this.generateStars(destination.rating);
    const highlights = destination.highlights
      ? destination.highlights.slice(0, 3).join(" • ")
      : "";

    return `
            <div class="destination-card" data-id="${destination.id}">
                <img src="${destination.image_url}" alt="${
      destination.name
    }" class="destination-image">
                <div class="destination-content">
                    <h3 class="destination-title">${destination.name}</h3>
                    <div class="destination-location">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>${destination.city}, ${destination.country}</span>
                    </div>
                    <p class="destination-description">${
                      destination.description
                    }</p>
                    <div class="destination-meta">
                        <div class="destination-rating">
                            <span class="stars">${stars}</span>
                            <span class="rating-text">${
                              destination.rating
                            }</span>
                        </div>
                        <div class="destination-price">${
                          destination.price
                        }</div>
                    </div>
                    ${
                      highlights
                        ? `<div class="destination-highlights">${highlights}</div>`
                        : ""
                    }
                    <button class="destination-button" onclick="destinationsPage.generateVisualization('${
                      destination.id
                    }')">
                        <i class="fas fa-magic"></i>
                        See Me There
                    </button>
                </div>
            </div>
        `;
  }

  generateStars(rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);

    let starsHTML = "";
    for (let i = 0; i < fullStars; i++) {
      starsHTML += "<span>★</span>";
    }
    if (hasHalfStar) {
      starsHTML += "<span>☆</span>";
    }
    for (let i = 0; i < emptyStars; i++) {
      starsHTML += "<span>☆</span>";
    }

    return starsHTML;
  }

  setupCardInteractions() {
    const cards = document.querySelectorAll(".destination-card");
    cards.forEach((card) => {
      card.addEventListener("click", (e) => {
        if (!e.target.classList.contains("destination-button")) {
          const id = card.dataset.id;
          this.viewDestination(id);
        }
      });
    });
  }

  viewDestination(id) {
    const destination = this.destinations.find((d) => d.id === id);
    if (destination) {
      // Show destination details in a modal or navigate to detail page
      uiComponents.showToast(`Viewing ${destination.name}`, "success");
    }
  }

  async generateVisualization(destinationId) {
    if (!this.uploadedPhotoUrl) {
      uiComponents.showToast("Please upload a photo first!", "warning");
      return;
    }

    const destination = this.destinations.find((d) => d.id === destinationId);
    if (!destination) {
      uiComponents.showToast("Destination not found", "error");
      return;
    }

    try {
      uiComponents.showToast("Generating visualization...", "success");

      const backendAvailable = await this.api.checkBackendHealth();

      if (backendAvailable) {
        // Use real API
        const response = await this.api.generateVisualization(
          this.uploadedPhotoUrl,
          destinationId
        );
        if (response.success) {
          uiComponents.showToast(
            "Visualization generated successfully!",
            "success"
          );
          // Navigate to visualizations page
          window.location.href = "visualizations.html";
        } else {
          throw new Error("Failed to generate visualization");
        }
      } else {
        // Simulate generation for demo
        await this.simulateVisualizationGeneration();
        uiComponents.showToast(
          "Demo: Visualization generated successfully!",
          "success"
        );
        window.location.href = "visualizations.html";
      }
    } catch (error) {
      console.error("Visualization generation failed:", error);
      uiComponents.showToast(
        "Failed to generate visualization. Please try again.",
        "error"
      );
    }
  }

  async simulateVisualizationGeneration() {
    return new Promise((resolve) => {
      setTimeout(resolve, 2000 + Math.random() * 2000);
    });
  }

  showEmptyState() {
    const destinationsGrid = document.querySelector(".destinations-grid");
    const emptyState = document.querySelector(".empty-state");

    if (destinationsGrid) destinationsGrid.style.display = "none";
    if (emptyState) emptyState.style.display = "block";
  }
}

// Initialize destinations page
const destinationsPage = new DestinationsPage();
window.destinationsPage = destinationsPage;
