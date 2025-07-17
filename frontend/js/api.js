// Simple API Service with Fallback Data
class APIService {
  constructor() {
    this.baseURL = "http://localhost:8000/api";
  }

  async checkBackendHealth() {
    try {
      const response = await fetch(`${this.baseURL}/health`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      return response.ok;
    } catch (error) {
      console.error("Backend health check failed:", error);
      return false;
    }
  }

  // Add a mock destinations method for destinations.js
  getMockDestinations() {
    return [
      {
        id: "tokyo",
        name: "Tokyo",
        country: "Japan",
        description: "Modern metropolis with ancient traditions.",
      },
      {
        id: "paris",
        name: "Paris",
        country: "France",
        description: "City of light and romance.",
      },
      {
        id: "new-york",
        name: "New York",
        country: "USA",
        description: "The city that never sleeps.",
      },
    ];
  }

  async getDestinations() {
    try {
      const response = await fetch(`${this.baseURL}/destinations`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });
      if (response.ok) {
        return await response.json();
      } else {
        // fallback to mock data
        return this.getMockDestinations();
      }
    } catch (error) {
      console.error("Failed to fetch destinations:", error);
      return this.getMockDestinations();
    }
  }

  // Get Continents with Fallback Data
  async getContinents() {
    try {
      console.log("Getting continents...");
      // Try the backend first
      const response = await fetch(`${this.baseURL}/continents`, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      });

      if (response.ok) {
        const data = await response.json();
        console.log("Backend continents:", data);
        return { success: true, data: data };
      } else {
        throw new Error("Backend continents failed");
      }
    } catch (error) {
      console.log("Using fallback continents data");
      // Return fallback data
      return {
        success: true,
        data: [
          {
            name: "Asia",
            count: 48,
            description:
              "Largest continent with diverse cultures, ancient civilizations, and modern cities",
            visual_theme: "diverse landscapes and cultures",
          },
          {
            name: "Europe",
            count: 44,
            description:
              "Historic continent with rich culture, art, and architecture",
            visual_theme: "historic cities and cultural heritage",
          },
          {
            name: "North America",
            count: 23,
            description:
              "Vast continent with diverse landscapes from Arctic to tropical",
            visual_theme: "natural wonders and modern cities",
          },
          {
            name: "Africa",
            count: 54,
            description:
              "Continent of incredible wildlife, ancient history, and diverse cultures",
            visual_theme: "wildlife and natural beauty",
          },
          {
            name: "Oceania",
            count: 14,
            description:
              "Island continent with stunning beaches and unique wildlife",
            visual_theme: "island paradise and marine life",
          },
          {
            name: "South America",
            count: 12,
            description:
              "Continent of Amazon rainforest, Andes mountains, and vibrant cultures",
            visual_theme: "rainforest and mountain landscapes",
          },
          {
            name: "Antarctica",
            count: 0,
            description:
              "Frozen continent of pristine wilderness and scientific research",
            visual_theme: "ice and snow landscapes",
          },
        ],
      };
    }
  }

  // Get Countries with Fallback Data
  async getCountriesByContinent(continentName) {
    console.log("Getting countries for:", continentName);
    // Return fallback data
    const fallbackCountries = {
      Asia: [
        {
          name: "Japan",
          description:
            "Land of the rising sun with ancient traditions and modern technology",
          cities: ["Tokyo", "Kyoto", "Osaka"],
        },
        {
          name: "Thailand",
          description: "Land of smiles with beautiful beaches and rich culture",
          cities: ["Bangkok", "Phuket", "Chiang Mai"],
        },
        {
          name: "India",
          description:
            "Incredible diversity with ancient history and vibrant culture",
          cities: ["Mumbai", "Delhi", "Jaipur"],
        },
        {
          name: "Vietnam",
          description: "Stunning landscapes and delicious cuisine",
          cities: ["Ho Chi Minh City", "Hanoi", "Da Nang"],
        },
        {
          name: "South Korea",
          description: "Modern cities and traditional culture",
          cities: ["Seoul", "Busan", "Jeju"],
        },
      ],
      Europe: [
        {
          name: "France",
          description: "Art, culture, and culinary excellence",
          cities: ["Paris", "Lyon", "Nice"],
        },
        {
          name: "Italy",
          description: "Ancient history, art, and delicious food",
          cities: ["Rome", "Florence", "Venice"],
        },
        {
          name: "Spain",
          description: "Vibrant culture, beaches, and architecture",
          cities: ["Madrid", "Barcelona", "Seville"],
        },
        {
          name: "Germany",
          description: "Efficient cities and beautiful countryside",
          cities: ["Berlin", "Munich", "Hamburg"],
        },
        {
          name: "Netherlands",
          description: "Windmills, tulips, and cycling culture",
          cities: ["Amsterdam", "Rotterdam", "The Hague"],
        },
      ],
      "North America": [
        {
          name: "United States",
          description: "Land of opportunity with diverse landscapes",
          cities: ["New York", "Los Angeles", "Chicago"],
        },
        {
          name: "Canada",
          description: "Vast wilderness and friendly cities",
          cities: ["Toronto", "Vancouver", "Montreal"],
        },
        {
          name: "Mexico",
          description: "Rich culture and beautiful beaches",
          cities: ["Mexico City", "Cancun", "Guadalajara"],
        },
      ],
      Africa: [
        {
          name: "South Africa",
          description: "Diverse wildlife and stunning landscapes",
          cities: ["Cape Town", "Johannesburg", "Durban"],
        },
        {
          name: "Egypt",
          description: "Ancient pyramids and rich history",
          cities: ["Cairo", "Luxor", "Alexandria"],
        },
        {
          name: "Morocco",
          description: "Exotic markets and desert adventures",
          cities: ["Marrakech", "Casablanca", "Fez"],
        },
      ],
      Oceania: [
        {
          name: "Australia",
          description: "Unique wildlife and stunning coastlines",
          cities: ["Sydney", "Melbourne", "Brisbane"],
        },
        {
          name: "New Zealand",
          description: "Adventure paradise with natural beauty",
          cities: ["Auckland", "Wellington", "Christchurch"],
        },
      ],
      "South America": [
        {
          name: "Brazil",
          description: "Carnival spirit and Amazon rainforest",
          cities: ["Rio de Janeiro", "São Paulo", "Salvador"],
        },
        {
          name: "Argentina",
          description: "Tango culture and Patagonian wilderness",
          cities: ["Buenos Aires", "Córdoba", "Mendoza"],
        },
        {
          name: "Peru",
          description: "Ancient Incan ruins and diverse landscapes",
          cities: ["Lima", "Cusco", "Arequipa"],
        },
      ],
    };

    return { success: true, data: fallbackCountries[continentName] || [] };
  }

  // Get Cities with Fallback Data
  async getCitiesByCountry(countryName) {
    console.log("Getting cities for:", countryName);
    // Return fallback data
    const fallbackCities = {
      Japan: [
        {
          id: "tokyo",
          name: "Tokyo",
          description: "Modern metropolis with ancient traditions",
          areas: ["Shibuya", "Shinjuku", "Harajuku"],
        },
        {
          id: "kyoto",
          name: "Kyoto",
          description: "Ancient capital with temples and gardens",
          areas: ["Gion", "Arashiyama", "Higashiyama"],
        },
        {
          id: "osaka",
          name: "Osaka",
          description: "Food capital with vibrant nightlife",
          areas: ["Dotonbori", "Namba", "Umeda"],
        },
      ],
      France: [
        {
          id: "paris",
          name: "Paris",
          description: "City of light with art and romance",
          areas: ["Eiffel Tower", "Louvre", "Montmartre"],
        },
        {
          id: "lyon",
          name: "Lyon",
          description: "Gastronomic capital of France",
          areas: ["Vieux Lyon", "Presqu'île", "Croix-Rousse"],
        },
        {
          id: "nice",
          name: "Nice",
          description: "Beautiful coastal city on the French Riviera",
          areas: ["Promenade des Anglais", "Old Town", "Cimiez"],
        },
      ],
      "United States": [
        {
          id: "new-york",
          name: "New York",
          description: "The city that never sleeps",
          areas: ["Manhattan", "Brooklyn", "Queens"],
        },
        {
          id: "los-angeles",
          name: "Los Angeles",
          description: "Entertainment capital of the world",
          areas: ["Hollywood", "Venice Beach", "Downtown"],
        },
        {
          id: "chicago",
          name: "Chicago",
          description: "Windy city with amazing architecture",
          areas: ["Loop", "Magnificent Mile", "Wicker Park"],
        },
      ],
      Australia: [
        {
          id: "sydney",
          name: "Sydney",
          description: "Harbor city with iconic opera house",
          areas: ["CBD", "Bondi Beach", "The Rocks"],
        },
        {
          id: "melbourne",
          name: "Melbourne",
          description: "Cultural capital with great coffee",
          areas: ["CBD", "St Kilda", "Fitzroy"],
        },
      ],
    };

    return { success: true, data: fallbackCities[countryName] || [] };
  }

  // Get Areas with Fallback Data
  async getAreasByCity(cityName) {
    console.log("Getting areas for:", cityName);
    // Return fallback data
    const fallbackAreas = {
      Tokyo: [
        {
          id: "shibuya",
          name: "Shibuya",
          description: "Fashion and youth culture district",
          activities: ["Shopping", "People watching", "Nightlife"],
        },
        {
          id: "shinjuku",
          name: "Shinjuku",
          description: "Business and entertainment district",
          activities: ["Skyscrapers", "Golden Gai", "Shinjuku Gyoen"],
        },
        {
          id: "harajuku",
          name: "Harajuku",
          description: "Fashion and street culture",
          activities: ["Takeshita Street", "Meiji Shrine", "Yoyogi Park"],
        },
      ],
      Paris: [
        {
          id: "eiffel",
          name: "Eiffel Tower Area",
          description: "Iconic landmark and surrounding gardens",
          activities: ["Eiffel Tower", "Champ de Mars", "Trocadéro"],
        },
        {
          id: "louvre",
          name: "Louvre District",
          description: "Art and culture center",
          activities: ["Louvre Museum", "Tuileries Garden", "Palais Royal"],
        },
        {
          id: "montmartre",
          name: "Montmartre",
          description: "Artistic hilltop neighborhood",
          activities: ["Sacré-Cœur", "Place du Tertre", "Moulin Rouge"],
        },
      ],
      "New York": [
        {
          id: "manhattan",
          name: "Manhattan",
          description: "Heart of NYC with iconic landmarks",
          activities: ["Times Square", "Central Park", "Broadway"],
        },
        {
          id: "brooklyn",
          name: "Brooklyn",
          description: "Trendy borough with great food",
          activities: ["Brooklyn Bridge", "Williamsburg", "DUMBO"],
        },
      ],
    };

    return { success: true, data: fallbackAreas[cityName] || [] };
  }

  // Generate Itinerary
  async generateItinerary(destinationId, preferences) {
    try {
      const response = await fetch(`${this.baseURL}/generate-itinerary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          destinationId: destinationId,
          preferences: preferences,
          prompt: "", // Optionally, you can build a prompt here if needed
        }),
      });
      if (response.ok) {
        const data = await response.json();
        // The backend returns { success, itinerary, message }
        if (data.success && data.itinerary) {
          return { success: true, data: data.itinerary };
        } else {
          return {
            success: false,
            error: data.message || "No itinerary returned",
          };
        }
      } else {
        return { success: false, error: `HTTP ${response.status}` };
      }
    } catch (error) {
      console.error("Failed to fetch itinerary:", error);
      return { success: false, error: error.message };
    }
  }

  // Generate Image
  async generateDestinationImage(destinationId, userPhotoUrl) {
    console.log("Generating image for:", destinationId);
    // Return fallback image
    const image = {
      url: `https://source.unsplash.com/800x600/?${encodeURIComponent(
        destinationId + " travel"
      )}`,
      prompt: `Travel photo of ${destinationId}`,
    };

    return { success: true, data: image };
  }

  // Generate Recommendations
  async generatePersonalizedRecommendations(preferences) {
    try {
      const response = await fetch(
        `${this.baseURL}/generate-personalized-recommendations`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(preferences),
        }
      );
      if (response.ok) {
        return await response.json();
      } else {
        throw new Error("Failed to fetch recommendations");
      }
    } catch (error) {
      console.error("Failed to fetch recommendations:", error);
      return { success: false, data: null, error: error.message };
    }
  }

  // Get Recommendations (alias for generatePersonalizedRecommendations)
  async getRecommendations(preferences) {
    return this.generatePersonalizedRecommendations(preferences);
  }

  // Search Flights
  async searchFlights(searchParams) {
    console.log("Searching flights:", searchParams);
    // Return fallback flight data
    const flights = [
      {
        id: "flight1",
        airline: "Sample Airlines",
        departure: searchParams.origin,
        arrival: searchParams.destination,
        departureTime: "10:00 AM",
        arrivalTime: "2:00 PM",
        duration: "4h",
        price: "$299",
      },
    ];

    return { success: true, data: flights };
  }

  // Search Hotels
  async searchHotels(searchParams) {
    console.log("Searching hotels:", searchParams);
    // Return fallback hotel data
    const hotels = [
      {
        id: "hotel1",
        name: "Sample Hotel",
        location: searchParams.cityCode,
        rating: 4.5,
        price: "$150/night",
        amenities: ["WiFi", "Pool", "Restaurant"],
      },
    ];

    return { success: true, data: hotels };
  }

  // Filter Destinations
  async filterDestinations(criteria) {
    console.log("Filtering destinations:", criteria);
    // Return fallback filtered destinations
    return { success: true, data: [] };
  }

  async getFlights({ from, to, depart, adults }) {
    try {
      const response = await fetch(`${this.baseURL}/search-flights`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          origin: from,
          destination: to,
          departure_date: depart,
          adults: adults,
        }),
      });
      if (response.ok) {
        return await response.json();
      } else {
        throw new Error("Failed to search flights");
      }
    } catch (error) {
      console.error("Flight search error:", error);
      throw error;
    }
  }

  // Add the missing generatePhotoAppImage method
  async generatePhotoAppImage(file, prompt) {
    try {
      const formData = new FormData();
      formData.append("selfie", file);
      formData.append("prompt", prompt);

      const response = await fetch(`${this.baseURL}/generate-photo-app-image`, {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        return await response.json();
      } else {
        throw new Error("Failed to generate photo app image");
      }
    } catch (error) {
      console.error("Photo app image generation error:", error);
      throw error;
    }
  }
}
