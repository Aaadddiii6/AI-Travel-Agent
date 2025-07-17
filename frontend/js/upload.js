// AI Generation Page JavaScript
class UploadPage {
  constructor() {
    this.api = new APIService();
    this.currentFile = null;
    this.lightxFile = null;
    this.init();
  }

  init() {
    this.setupLightXUpload();
    this.setupDalleGeneration();
    this.setupLightXGeneration();
    this.setupFaceSwapVisualization();
    this.checkBackendStatus();
  }

  async checkBackendStatus() {
    const backendAvailable = await this.api.checkBackendHealth();
    if (!backendAvailable) {
      uiComponents.showToast(
        "Backend server is not available. Using demo mode.",
        "warning"
      );
    }
  }

  setupLightXUpload() {
    const dropZone = document.querySelector("#lightx-upload-zone");
    const fileInput = document.querySelector("#lightx-file-input");
    const previewContainer = document.querySelector("#lightx-upload-preview");
    const inputArea = document.querySelector("#lightx-input-area");

    if (dropZone && fileInput && previewContainer) {
      this.setupLightXUploadHandlers(
        dropZone,
        fileInput,
        previewContainer,
        inputArea
      );
    }
  }

  setupLightXUploadHandlers(dropZone, fileInput, previewContainer, inputArea) {
    // Drag and drop events
    dropZone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropZone.classList.add("drag-over");
    });

    dropZone.addEventListener("dragleave", () => {
      dropZone.classList.remove("drag-over");
    });

    dropZone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropZone.classList.remove("drag-over");

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        this.handleLightXFileSelect(
          files[0],
          fileInput,
          previewContainer,
          inputArea
        );
      }
    });

    // Click to upload
    const chooseBtn = document.querySelector("#choose-lightx-photo-btn");
    if (chooseBtn) {
      chooseBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        fileInput.click();
      });
    }

    // File input change
    fileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        this.handleLightXFileSelect(
          e.target.files[0],
          fileInput,
          previewContainer,
          inputArea
        );
      }
    });

    // Remove preview
    const removeBtn = document.querySelector("#lightx-preview-remove");
    if (removeBtn) {
      removeBtn.addEventListener("click", (e) => {
        e.preventDefault();
        this.removeLightXPreview();
      });
    }
  }

  handleLightXFileSelect(file, fileInput, previewContainer, inputArea) {
    const validation = this.validateFile(file);
    if (!validation.valid) {
      uiComponents.showToast(validation.error, "error");
      return;
    }

    // Update file input
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;

    // Store file for LightX processing
    this.lightxFile = file;

    // Show preview
    this.showLightXImagePreview(file, previewContainer);

    // Show input area
    if (inputArea) {
      inputArea.style.display = "block";
    }

    uiComponents.showToast("Photo selected for LightX enhancement!", "success");
  }

  showLightXImagePreview(file, container) {
    const reader = new FileReader();
    reader.onload = (e) => {
      container.innerHTML = `
                <div class="preview-container">
                    <img src="${e.target.result}" alt="Preview" class="preview-image">
                    <button class="preview-remove" id="lightx-preview-remove">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="preview-status">
                    <span class="status-icon">✓</span>
                    <span>Photo ready for enhancement</span>
                </div>
            `;

      // Re-attach remove button event
      const removeBtn = container.querySelector("#lightx-preview-remove");
      if (removeBtn) {
        removeBtn.addEventListener("click", (e) => {
          e.preventDefault();
          this.removeLightXPreview();
        });
      }
    };
    reader.readAsDataURL(file);
  }

  removeLightXPreview() {
    const container = document.querySelector("#lightx-upload-preview");
    const inputArea = document.querySelector("#lightx-input-area");

    if (container) {
      container.innerHTML = "";
    }

    if (inputArea) {
      inputArea.style.display = "none";
    }

    // Clear file input
    const fileInput = document.querySelector("#lightx-file-input");
    if (fileInput) {
      fileInput.value = "";
    }

    this.lightxFile = null;
  }

  validateFile(
    file,
    allowedTypes = ["image/jpeg", "image/png", "image/webp"],
    maxSize = 10 * 1024 * 1024
  ) {
    if (!file) {
      return { valid: false, error: "Please select a file" };
    }

    if (!allowedTypes.includes(file.type)) {
      return {
        valid: false,
        error: "Please select a valid image file (JPEG, PNG, or WebP)",
      };
    }

    if (file.size > maxSize) {
      return { valid: false, error: "File size must be less than 10MB" };
    }

    return { valid: true };
  }

  showImagePreview(file, container) {
    const reader = new FileReader();
    reader.onload = (e) => {
      container.innerHTML = `
                <div class="preview-container">
                    <img src="${e.target.result}" alt="Preview" class="preview-image">
                    <button class="preview-remove" onclick="uploadPage.removeImagePreview(this)">×</button>
                </div>
                <div class="preview-status">
                    <span class="status-icon">✓</span>
                    <span>Image ready for upload</span>
                </div>
            `;
    };
    reader.readAsDataURL(file);
  }

  removeImagePreview(button) {
    const container = button.closest(".upload-preview");
    if (container) {
      container.innerHTML = "";
    }

    // Clear file input
    const fileInput = document.querySelector("#file-input");
    if (fileInput) {
      fileInput.value = "";
    }
  }

  setupFormSubmission() {
    const form = document.querySelector(".upload-form");
    const submitBtn = document.querySelector(".upload-btn");

    if (form) {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        this.handleUpload();
      });
    }

    if (submitBtn) {
      submitBtn.addEventListener("click", (e) => {
        e.preventDefault();
        this.handleUpload();
      });
    }
  }

  setupProgressIndicator() {
    // Update progress based on current step
    this.updateProgress(1);
  }

  updateProgress(step) {
    const steps = document.querySelectorAll(".progress-step");
    steps.forEach((stepEl, index) => {
      if (index < step) {
        stepEl.classList.add("active");
      } else {
        stepEl.classList.remove("active");
      }
    });
  }

  async handleUpload() {
    const fileInput = document.querySelector("#file-input");
    const submitBtn = document.querySelector(".upload-btn");
    const uploadSection = document.querySelector(".upload-section");

    if (!fileInput.files.length) {
      uiComponents.showToast("Please select an image first", "error");
      return;
    }

    const file = fileInput.files[0];
    const validation = this.validateFile(file);

    if (!validation.valid) {
      uiComponents.showToast(validation.error, "error");
      return;
    }

    this.currentFile = file;

    // Show loading state with progress
    const loading = this.showUploadProgress(uploadSection);
    submitBtn.disabled = true;
    this.updateProgress(2);

    try {
      // Check if backend is available
      const backendAvailable = await this.api.checkBackendHealth();

      if (backendAvailable) {
        // Use real API with progress tracking
        const result = await this.api.uploadPhoto(file, (progress) => {
          this.updateUploadProgress(loading, progress);
        });

        console.log("Upload result:", result); // Debug log

        if (result.success) {
          this.uploadedPhotoUrl = result.photo_url;
          console.log("Photo URL set to:", this.uploadedPhotoUrl); // Debug log
          uiComponents.showToast("Photo uploaded successfully!", "success");
        } else {
          throw new Error("Upload failed");
        }
      } else {
        // Use mock data for demo
        this.uploadedPhotoUrl = this.getMockPhotoUrl(file);
        console.log("Mock photo URL set to:", this.uploadedPhotoUrl); // Debug log
        await this.simulateProcessing();
        uiComponents.showToast(
          "Demo mode: Photo processed successfully!",
          "success"
        );
      }

      // Save to local storage
      this.saveUploadResult();

      // Show success state
      this.showSuccessState();
      this.updateProgress(3);
    } catch (error) {
      console.error("Upload failed:", error);
      uiComponents.showToast(`Upload failed: ${error.message}`, "error");
      this.updateProgress(1);
    } finally {
      this.hideLoading(uploadSection);
      submitBtn.disabled = false;
    }
  }

  showUploadProgress(container) {
    const progressContainer = document.createElement("div");
    progressContainer.className = "upload-loading";
    progressContainer.innerHTML = `
            <div class="loading-spinner"></div>
            <div class="loading-text">Uploading your photo...</div>
            <div class="loading-subtext">Please wait while we process your image</div>
            <div class="progress-bar-container">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 0%"></div>
                </div>
                <div class="progress-text">0%</div>
            </div>
        `;

    container.style.position = "relative";
    container.appendChild(progressContainer);
    return progressContainer;
  }

  updateUploadProgress(progressContainer, percent) {
    const progressFill = progressContainer.querySelector(".progress-fill");
    const progressText = progressContainer.querySelector(".progress-text");

    if (progressFill && progressText) {
      progressFill.style.width = `${percent}%`;
      progressText.textContent = `${Math.round(percent)}%`;
    }
  }

  hideLoading(element) {
    const loading = element.querySelector(".upload-loading");
    if (loading) {
      loading.remove();
    }
  }

  getMockPhotoUrl(file) {
    // Create a mock URL for demo purposes
    return URL.createObjectURL(file);
  }

  async simulateProcessing() {
    // Simulate processing time
    return new Promise((resolve) => {
      setTimeout(resolve, 2000 + Math.random() * 2000);
    });
  }

  showSuccessState() {
    const uploadSection = document.querySelector(".upload-section");
    const successState = document.querySelector(".success-state");

    if (uploadSection && successState) {
      uploadSection.style.display = "none";
      successState.style.display = "block";

      // Update success content
      this.updateSuccessContent();
    }
  }

  updateSuccessContent() {
    const successTitle = document.querySelector(".success-title");
    const successDescription = document.querySelector(".success-description");
    const viewDestinationsBtn = document.querySelector(
      ".success-buttons .btn-primary"
    );

    if (successTitle) {
      successTitle.textContent = `Photo Uploaded Successfully!`;
    }

    if (successDescription) {
      successDescription.textContent = `Your photo has been uploaded and is ready for destination matching. Let's find you the perfect travel destinations!`;
    }

    if (viewDestinationsBtn) {
      // Removed 'Browse Destinations' button and navigation to keep user in SPA flow
    }
  }

  // Removed navigateToDestinations to prevent navigation to Explore Destinations page

  saveUploadResult() {
    if (this.uploadedPhotoUrl) {
      const uploadData = {
        photoUrl: this.uploadedPhotoUrl,
        timestamp: new Date().toISOString(),
        fileName: this.currentFile ? this.currentFile.name : "unknown",
      };

      localStorage.setItem("lastUpload", JSON.stringify(uploadData));
    }
  }

  loadSavedData() {
    const savedUpload = localStorage.getItem("lastUpload");
    if (savedUpload) {
      try {
        const uploadData = JSON.parse(savedUpload);
        const timeDiff = Date.now() - new Date(uploadData.timestamp).getTime();
        const hoursDiff = timeDiff / (1000 * 60 * 60);

        // Show recent upload if less than 24 hours old
        if (hoursDiff < 24) {
          this.showRecentUpload(uploadData);
        }
      } catch (error) {
        console.error("Error loading saved upload:", error);
      }
    }
  }

  showRecentUpload(uploadData) {
    const recentUpload = document.createElement("div");
    recentUpload.className = "upload-info";
    recentUpload.innerHTML = `
            <div class="info-icon">📋</div>
            <div class="info-title">Recent Upload Available</div>
            <div class="info-content">
                <p>We found a recent upload from ${this.formatDate(
                  uploadData.timestamp
                )}</p>
                <p>File: ${uploadData.fileName}</p>
                <button class="btn btn-secondary" onclick="uploadPage.loadRecentUpload()">Use Recent Upload</button>
            </div>
        `;

    const uploadSection = document.querySelector(".upload-section");
    if (uploadSection) {
      uploadSection.appendChild(recentUpload);
    }
  }

  setupDalleGeneration() {
    const generateBtn = document.querySelector("#generate-dalle-btn");
    const textPrompt = document.querySelector("#text-prompt");
    const imageStyle = document.querySelector("#image-style");
    const generatedGrid = document.querySelector("#dalle-images-grid");
    const generationLoading = document.querySelector("#dalle-loading");

    if (generateBtn) {
      generateBtn.addEventListener("click", async () => {
        const prompt = textPrompt ? textPrompt.value.trim() : "";
        const style = imageStyle ? imageStyle.value : "";

        if (!prompt) {
          uiComponents.showToast(
            "Please enter a description for your image",
            "error"
          );
          return;
        }

        await this.generateDalleImage(
          prompt,
          style,
          generatedGrid,
          generationLoading
        );
      });
    }

    // Allow Enter key to generate
    if (textPrompt) {
      textPrompt.addEventListener("keypress", async (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          const prompt = textPrompt.value.trim();
          const style = imageStyle ? imageStyle.value : "";

          if (prompt) {
            await this.generateDalleImage(
              prompt,
              style,
              generatedGrid,
              generationLoading
            );
          }
        }
      });
    }
  }

  setupLightXGeneration() {
    const generateBtn = document.querySelector("#generate-lightx-btn");
    const lightxPrompt = document.querySelector("#lightx-prompt");
    const generatedGrid = document.querySelector("#lightx-images-grid");
    const generationLoading = document.querySelector("#lightx-loading");

    if (generateBtn) {
      generateBtn.addEventListener("click", async () => {
        const prompt = lightxPrompt ? lightxPrompt.value.trim() : "";

        if (!this.lightxFile) {
          uiComponents.showToast("Please upload a photo first", "error");
          return;
        }

        if (!prompt) {
          uiComponents.showToast("Please enter an enhancement prompt", "error");
          return;
        }

        await this.generateLightXImage(
          prompt,
          generatedGrid,
          generationLoading
        );
      });
    }

    // Allow Enter key to generate
    if (lightxPrompt) {
      lightxPrompt.addEventListener("keypress", async (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          const prompt = lightxPrompt.value.trim();

          if (prompt && this.lightxFile) {
            await this.generateLightXImage(
              prompt,
              generatedGrid,
              generationLoading
            );
          }
        }
      });
    }
  }

  async generateDalleImage(prompt, style, generatedGrid, generationLoading) {
    if (prompt.length < 10) {
      uiComponents.showToast(
        "Please provide a more detailed description (at least 10 characters)",
        "error"
      );
      return;
    }

    // Show loading state
    generationLoading.style.display = "flex";
    generatedGrid.style.display = "none";

    try {
      const response = await this.api.generateTextToImage(prompt, style);

      if (response.success) {
        this.addGeneratedImage(
          generatedGrid,
          prompt,
          response.image_url,
          response.provider
        );
        uiComponents.showToast(
          "DALL-E image generated successfully!",
          "success"
        );
      } else {
        throw new Error(response.message || "Failed to generate image");
      }
    } catch (error) {
      console.error("DALL-E generation failed:", error);
      uiComponents.showToast(
        `Failed to generate image: ${error.message}`,
        "error"
      );
    } finally {
      // Hide loading state
      generationLoading.style.display = "none";
      generatedGrid.style.display = "flex";
    }
  }

  async generateLightXImage(prompt, generatedGrid, generationLoading) {
    if (prompt.length < 5) {
      uiComponents.showToast(
        "Please provide a more detailed enhancement prompt (at least 5 characters)",
        "error"
      );
      return;
    }

    // Show loading state
    generationLoading.style.display = "flex";
    generatedGrid.style.display = "none";

    try {
      // Convert file to base64
      const base64Image = await this.fileToBase64(this.lightxFile);

      const response = await this.api.generateLightXImage(prompt, base64Image);

      if (response.success && response.images && response.images.length > 0) {
        response.images.forEach((image) => {
          this.addGeneratedImage(generatedGrid, prompt, image.url, "lightx");
        });
        uiComponents.showToast(
          "LightX enhancement completed successfully!",
          "success"
        );
      } else {
        throw new Error(response.message || "Failed to enhance image");
      }
    } catch (error) {
      console.error("LightX generation failed:", error);

      // Provide more helpful error messages
      let errorMessage = error.message;
      if (error.message.includes("No face detected")) {
        errorMessage =
          "No face detected in the image. Please upload a clear photo with a visible human face.";
      } else if (error.message.includes("LightX AI couldn't process")) {
        errorMessage =
          "LightX AI couldn't process this image. Please try with a clearer human portrait photo.";
      } else if (error.message.includes("LightX AI works best")) {
        errorMessage =
          "LightX AI works best with human portraits. Please upload a photo with a clear face.";
      }

      uiComponents.showToast(
        `Failed to enhance image: ${errorMessage}`,
        "error"
      );
    } finally {
      // Hide loading state
      generationLoading.style.display = "none";
      generatedGrid.style.display = "flex";
    }
  }

  fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => {
        // Remove the data URL prefix to get just the base64 data
        const base64 = reader.result.split(",")[1];
        resolve(base64);
      };
      reader.onerror = (error) => reject(error);
    });
  }

  addGeneratedImage(container, prompt, imageUrl, provider) {
    // Remove placeholder if it exists
    const placeholder = container.querySelector(".placeholder-message");
    if (placeholder) {
      placeholder.remove();
    }

    const imageItem = document.createElement("div");
    imageItem.className = "generated-image-item";

    const providerBadge =
      provider === "openai"
        ? "OpenAI DALL-E"
        : provider === "deepai"
        ? "DeepAI"
        : provider === "lightx"
        ? "LightX AI"
        : "Placeholder";

    imageItem.innerHTML = `
            <img src="${imageUrl}" alt="Generated image" class="generated-image" onerror="this.src='https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=400&h=400&fit=crop'">
            <div class="generated-image-info">
                <p class="generated-prompt">${prompt}</p>
                <div class="generated-actions">
                    <button class="generated-action-btn" onclick="uploadPage.downloadImage('${imageUrl}', '${prompt}')">
                        <i class="fas fa-download"></i>
                    </button>
                    <button class="generated-action-btn secondary" onclick="uploadPage.shareImage('${imageUrl}', '${prompt}')">
                        <i class="fas fa-share"></i>
                    </button>
                </div>
            </div>
            <div style="font-size: 0.8rem; color: #95a5a6; margin-top: 0.5rem;">
                Generated with ${providerBadge}
            </div>
        `;

    container.appendChild(imageItem);
  }

  downloadImage(imageUrl, prompt) {
    const link = document.createElement("a");
    link.href = imageUrl;
    link.download = `generated-image-${Date.now()}.jpg`;
    link.target = "_blank";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    uiComponents.showToast("Image download started!", "success");
  }

  shareImage(imageUrl, prompt) {
    if (navigator.share) {
      navigator
        .share({
          title: "AI Generated Image",
          text: `Check out this AI-generated image: ${prompt}`,
          url: imageUrl,
        })
        .catch(() => {
          this.copyToClipboard(imageUrl);
        });
    } else {
      this.copyToClipboard(imageUrl);
    }
  }

  copyToClipboard(text) {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        uiComponents.showToast("Image URL copied to clipboard!", "success");
      })
      .catch(() => {
        uiComponents.showToast("Failed to copy to clipboard", "error");
      });
  }

  formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }

  loadRecentUpload() {
    const savedUpload = localStorage.getItem("lastUpload");
    if (savedUpload) {
      const uploadData = JSON.parse(savedUpload);
      this.uploadedPhotoUrl = uploadData.photoUrl;
      this.showSuccessState();
      this.updateProgress(3);
      uiComponents.showToast("Recent upload loaded successfully!", "success");
    }
  }

  // Reset upload form
  resetUpload() {
    const fileInput = document.querySelector("#file-input");
    const previewContainer = document.querySelector(".upload-preview");
    const uploadSection = document.querySelector(".upload-section");
    const successState = document.querySelector(".success-state");

    if (fileInput) fileInput.value = "";
    if (previewContainer) previewContainer.innerHTML = "";
    if (uploadSection) uploadSection.style.display = "block";
    if (successState) successState.style.display = "none";

    this.currentFile = null;
    this.uploadedPhotoUrl = null;
    this.updateProgress(1);
  }

  // NEW: Setup Face Swap Visualization logic
  setupFaceSwapVisualization() {
    const fileInput = document.getElementById("face-swap-file-input");
    const promptInput = document.getElementById("face-swap-prompt");
    const generateBtn = document.getElementById("generate-face-swap-btn");
    const imagesGrid = document.getElementById("face-swap-images-grid");
    const loadingDiv = document.getElementById("face-swap-loading");

    if (!fileInput || !promptInput || !generateBtn || !imagesGrid) return;

    generateBtn.addEventListener("click", async (e) => {
      e.preventDefault();
      if (!fileInput.files || fileInput.files.length === 0) {
        uiComponents.showToast("Please upload a selfie.", "error");
        return;
      }
      const promptValue = promptInput.value.trim();
      console.log("Prompt validation:", {
        rawValue: promptInput.value,
        trimmedValue: promptValue,
        length: promptValue.length,
        isValid: promptValue.length >= 10,
      });

      if (!promptValue || promptValue.length < 10) {
        uiComponents.showToast(
          "Please enter a prompt (at least 10 characters).",
          "error"
        );
        return;
      }
      // Show loading
      loadingDiv.style.display = "block";
      imagesGrid.innerHTML = "";
      try {
        // Call the new photo app image generator endpoint
        const result = await this.api.generatePhotoAppImage(
          fileInput.files[0],
          promptValue
        );
        if (
          !result.success ||
          !result.image_urls ||
          result.image_urls.length === 0
        ) {
          throw new Error(
            "Image generation failed: " + (result.error || "Unknown error")
          );
        }
        // Display generated images
        const backendBaseUrl = "http://localhost:8000";
        imagesGrid.innerHTML = result.image_urls
          .map(
            (url) =>
              `<div class=\"preview-container\">
             <img src=\"${backendBaseUrl}${url}\" alt=\"Visualization\" class=\"preview-image\">
             <button class=\"generated-action-btn\" onclick=\"uploadPage.downloadImage('${backendBaseUrl}${url}', 'AI Travel Visualization')\">
               <i class=\"fas fa-download\"></i> Download
             </button>
           </div>`
          )
          .join("");
        uiComponents.showToast("Visualization generated!", "success");
      } catch (err) {
        imagesGrid.innerHTML = `<div class=\"placeholder-message\"><i class=\"fas fa-exclamation-triangle\"></i><p>${err.message}</p></div>`;
        uiComponents.showToast(err.message, "error");
      } finally {
        loadingDiv.style.display = "none";
      }
    });
  }
}

// Initialize upload page
const uploadPage = new UploadPage();
window.uploadPage = uploadPage;
