
const fileInput = document.getElementById("file-input");
const browseButton = document.getElementById("browse-btn");
const chooseFileButton = document.getElementById("choose-file-btn");
const uploadZone = document.getElementById("upload-zone");
const selectedFile = document.getElementById("selected-file");
const removeButton = document.getElementById("remove-file");

let currentFile = null;
let currentUploadId = null;
let isUploading = false;

// Create upload and download buttons in the selected-file panel.
const uploadButton = document.createElement("button");
uploadButton.className = "primary-btn";
uploadButton.textContent = "Encrypt & Upload";
uploadButton.type = "button";
uploadButton.style.marginTop = "0";
uploadButton.hidden = true;

const downloadButton = document.createElement("button");
downloadButton.className = "secondary-btn";
downloadButton.textContent = "Download";
downloadButton.type = "button";
downloadButton.hidden = true;

selectedFile.insertBefore(uploadButton, removeButton);
selectedFile.insertBefore(downloadButton, removeButton);

function openFilePicker() {
    if (!isUploading) fileInput.click();
}

function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(2)} KB`;
    if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(2)} MB`;
    return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}

function setStatus(message) {
    uploadZone.querySelector("small").textContent = message;
}

function showFile(file) {
    if (!file || isUploading) return;

    currentFile = file;
    currentUploadId = null;

    document.getElementById("selected-name").textContent = file.name;
    document.getElementById("selected-size").textContent = formatSize(file.size);

    selectedFile.hidden = false;
    uploadButton.hidden = false;
    downloadButton.hidden = true;
    uploadButton.disabled = false;
    uploadButton.textContent = "Encrypt & Upload";

    document.getElementById("file-count").textContent = "0";
    document.getElementById("storage-used").textContent = "0 B";

    uploadZone.querySelector("h3").textContent = "File selected successfully";
    setStatus("Ready to encrypt and upload to private S3 storage.");
}

function clearFile() {
    if (isUploading) return;

    currentFile = null;
    currentUploadId = null;
    fileInput.value = "";

    selectedFile.hidden = true;
    uploadButton.hidden = true;
    downloadButton.hidden = true;

    document.getElementById("file-count").textContent = "0";
    document.getElementById("storage-used").textContent = "0 B";

    uploadZone.querySelector("h3").textContent = "Drop your file here";
    setStatus("Choose a file to begin.");
}

async function uploadCurrentFile() {
    if (!currentFile || isUploading) return;

    if (currentFile.size > 25 * 1024 * 1024) {
        setStatus("File exceeds the 25 MB upload limit.");
        return;
    }

    isUploading = true;
    uploadButton.disabled = true;
    uploadButton.textContent = "Uploading...";
    removeButton.disabled = true;
    setStatus("Encrypting and uploading your file to Amazon S3...");

    const formData = new FormData();
    formData.append("file", currentFile);

    try {
        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Upload failed.");
        }

        currentUploadId = result.upload_id;

        document.getElementById("file-count").textContent = "1";
        document.getElementById("storage-used").textContent =
            formatSize(currentFile.size);

        uploadButton.hidden = true;
        downloadButton.hidden = false;

        setStatus(
            `Upload successful! ${result.blocks} encrypted block(s) stored in S3.`
        );

    } catch (error) {
        console.error("CloudVault upload error:", error);
        setStatus(error.message || "Upload failed. Check the Flask terminal.");
        uploadButton.textContent = "Retry Upload";
        uploadButton.disabled = false;

    } finally {
        isUploading = false;
        removeButton.disabled = false;

        if (!uploadButton.hidden) {
            uploadButton.disabled = false;
        }
    }
}

async function downloadCurrentFile() {
    if (!currentUploadId) return;

    downloadButton.disabled = true;
    downloadButton.textContent = "Preparing...";

    try {
        const response = await fetch(
            `/api/download/${encodeURIComponent(currentUploadId)}`
        );

        if (!response.ok) {
            let message = "Download failed.";

            try {
                const error = await response.json();
                message = error.error || message;
            } catch (_) {}

            throw new Error(message);
        }

        const blob = await response.blob();
        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = objectUrl;
        link.download = `recovered_${currentFile?.name || "file"}`;

        document.body.appendChild(link);
        link.click();
        link.remove();

        setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
        setStatus("Download complete. Your recovered file is ready.");

    } catch (error) {
        console.error("CloudVault download error:", error);
        setStatus(error.message || "Download failed. Check the Flask terminal.");

    } finally {
        downloadButton.disabled = false;
        downloadButton.textContent = "Download";
    }
}

browseButton.addEventListener("click", openFilePicker);
chooseFileButton.addEventListener("click", openFilePicker);
uploadZone.addEventListener("click", openFilePicker);

uploadZone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openFilePicker();
    }
});

fileInput.addEventListener("change", () => {
    showFile(fileInput.files[0]);
});

uploadButton.addEventListener("click", uploadCurrentFile);
downloadButton.addEventListener("click", downloadCurrentFile);
removeButton.addEventListener("click", clearFile);

uploadZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    uploadZone.classList.add("dragging");
});

uploadZone.addEventListener("dragleave", () => {
    uploadZone.classList.remove("dragging");
});

uploadZone.addEventListener("drop", (event) => {
    event.preventDefault();
    uploadZone.classList.remove("dragging");
    showFile(event.dataTransfer.files[0]);
});
