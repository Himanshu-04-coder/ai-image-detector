"""
Grad-CAM Module - Explainability for AI-Generated Image Detector
==================================================================

Grad-CAM (Gradient-weighted Class Activation Mapping) shows WHICH regions
of an image most influenced the model's prediction, by:

1. Running a forward pass and getting the predicted class
2. Computing gradients of that class's score with respect to the feature
   maps of the last convolutional layer (layer4 in ResNet50)
3. Using those gradients as "importance weights" for each feature channel
4. Combining the weighted feature maps into a single heatmap
5. Overlaying that heatmap on the original image

Intuition: if a feature map channel's gradient is large and positive, it
means "increasing this feature would increase the predicted class score" -
so we weight that channel highly when building the heatmap. Regions with
high combined activation are the regions the model "looked at" most.

IMPORTANT FOR VIVA: Grad-CAM does NOT show ground truth reasoning, it shows
what the trained model's convolutional filters responded to strongly for
that specific prediction. It's a diagnostic/explainability tool, not proof
of correctness.

NOTE ON IMAGE SIZE: CIFAKE dataset images are only 32x32 pixels natively.
The output heatmap overlay is upscaled to DISPLAY_SIZE (default 512x512)
purely for human visibility - this does not affect the model's prediction
or the Grad-CAM computation itself, which happens at the model's actual
input resolution (64x64, as set in Phase 1 training).
"""

import os
import cv2
import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
from torchvision import transforms, models
import torch.nn as nn

# ============================================================
# Must match Phase 1 training script exactly
# ============================================================
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
IMG_SIZE = 64
CLASS_NAMES = ["FAKE", "REAL"]  # index 0 = FAKE, index 1 = REAL (as trained)

# Final output image size (for visibility only - CIFAKE source images are 32x32)
DISPLAY_SIZE = 512

inference_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])


def load_model(model_path, device):
    """
    Rebuilds the same ResNet50 architecture used in training and loads
    the saved weights.
    """
    model = models.resnet50(weights=None)  # no need to download pretrained weights again
    num_features = model.fc.in_features
    model.fc = nn.Linear(num_features, 2)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model = model.to(device)
    model.eval()
    return model


class GradCAM:
    """
    Manual Grad-CAM implementation using forward/backward hooks on
    ResNet50's layer4 (the last convolutional block before pooling).
    """

    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None

        # Hook to capture the feature maps during the forward pass
        target_layer.register_forward_hook(self._save_activation)
        # Hook to capture gradients during the backward pass
        target_layer.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, module, input, output):
        self.activations = output.detach()

    def _save_gradient(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def generate(self, input_tensor, class_idx=None):
        """
        Runs a forward + backward pass and computes the Grad-CAM heatmap.

        Args:
            input_tensor: preprocessed image tensor, shape (1, 3, H, W)
            class_idx: which class to explain. If None, uses the model's
                       own predicted class (most common use case).

        Returns:
            heatmap: 2D numpy array (H, W), normalized to [0, 1]
            predicted_class: int, the class index used
            confidence: float, softmax confidence for that class
        """
        self.model.zero_grad()

        output = self.model(input_tensor)              # shape (1, num_classes)
        probs = F.softmax(output, dim=1)

        if class_idx is None:
            class_idx = output.argmax(dim=1).item()

        confidence = probs[0, class_idx].item()

        # Backward pass only through the score of the target class
        score = output[0, class_idx]
        score.backward()

        gradients = self.gradients[0]      # shape (C, h, w)
        activations = self.activations[0]  # shape (C, h, w)

        # Global-average-pool the gradients over spatial dims -> per-channel weight
        weights = gradients.mean(dim=(1, 2))  # shape (C,)

        # Weighted sum of activation maps
        cam = torch.zeros(activations.shape[1:], dtype=torch.float32, device=activations.device)
        for i, w in enumerate(weights):
            cam += w * activations[i]

        cam = F.relu(cam)  # only keep features that positively influenced the class score

        cam = cam.cpu().numpy()
        # Normalize to [0, 1] for visualization
        if cam.max() > 0:
            cam = cam / cam.max()

        return cam, class_idx, confidence


def generate_gradcam(image_path, model, output_path, device=None, display_size=DISPLAY_SIZE):
    """
    Main entry point. Runs Grad-CAM on a single image and saves an
    upscaled overlay visualization.

    Args:
        image_path: path to the input image
        model: loaded PyTorch model (already on the correct device, eval mode)
        output_path: where to save the resulting heatmap overlay image
        device: torch device (cuda/cpu). If None, inferred from model.
        display_size: final output image width/height in pixels (for visibility,
                       since CIFAKE source images are only 32x32)

    Returns:
        dict with output_path, predicted_label, confidence
    """
    if device is None:
        device = next(model.parameters()).device

    # ---- Load and preprocess image ----
    original_image = Image.open(image_path).convert("RGB")
    input_tensor = inference_transform(original_image).unsqueeze(0).to(device)

    # ---- Run Grad-CAM ----
    target_layer = model.layer4[-1]  # last block of layer4, richest spatial features
    grad_cam = GradCAM(model, target_layer)
    cam, class_idx, confidence = grad_cam.generate(input_tensor)

    # ---- Upscale ORIGINAL image first (before overlay) for better visibility ----
    # Using INTER_CUBIC for smoother upscaling since source is only 32x32
    original_np = np.array(original_image)
    original_np = cv2.resize(original_np, (display_size, display_size), interpolation=cv2.INTER_CUBIC)

    # ---- Resize heatmap to match the upscaled display size ----
    cam_resized = cv2.resize(cam, (display_size, display_size), interpolation=cv2.INTER_CUBIC)

    # ---- Convert to color heatmap (jet colormap) ----
    heatmap_color = cv2.applyColorMap(np.uint8(255 * cam_resized), cv2.COLORMAP_JET)
    heatmap_color = cv2.cvtColor(heatmap_color, cv2.COLOR_BGR2RGB)

    # ---- Blend heatmap with upscaled original image (40% opacity) ----
    overlay = cv2.addWeighted(original_np, 0.6, heatmap_color, 0.4, 0)

    # ---- Save result ----
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    overlay_bgr = cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR)
    cv2.imwrite(output_path, overlay_bgr)

    predicted_label = CLASS_NAMES[class_idx]
    print(f"[{os.path.basename(image_path)}] -> {predicted_label} "
          f"(confidence: {confidence:.4f}) | heatmap saved to {output_path} "
          f"({display_size}x{display_size}px)")

    return {
        "output_path": output_path,
        "predicted_label": predicted_label,
        "confidence": confidence
    }


# ============================================================
# TEST SCRIPT - run this to visually verify Grad-CAM is working
# ============================================================
if __name__ == "__main__":
    import glob
    import random

    # ---- Paths (adjust if your Drive folder structure differs) ----
    SAVE_DIR = "/content/drive/MyDrive/ai-image-detector"
    MODEL_PATH = os.path.join(SAVE_DIR, "best_model.pth")
    TEST_DATA_DIR = "data/test"  # local Colab folder from Phase 1
    HEATMAP_OUTPUT_DIR = os.path.join(SAVE_DIR, "heatmaps")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    print("Loading model...")
    model = load_model(MODEL_PATH, device)
    print("Model loaded successfully.\n")

    # ---- Pick a few random sample images from REAL and FAKE test folders ----
    real_images = glob.glob(os.path.join(TEST_DATA_DIR, "REAL", "*.*"))
    fake_images = glob.glob(os.path.join(TEST_DATA_DIR, "FAKE", "*.*"))

    sample_images = random.sample(real_images, min(2, len(real_images))) + \
                     random.sample(fake_images, min(2, len(fake_images)))

    print(f"Testing Grad-CAM on {len(sample_images)} sample images...\n")

    os.makedirs(HEATMAP_OUTPUT_DIR, exist_ok=True)

    for idx, img_path in enumerate(sample_images):
        output_path = os.path.join(HEATMAP_OUTPUT_DIR, f"heatmap_{idx+1}.png")
        result = generate_gradcam(img_path, model, output_path, device)

    print(f"\nAll heatmaps saved to: {HEATMAP_OUTPUT_DIR}")
    print(f"Each image is upscaled to {DISPLAY_SIZE}x{DISPLAY_SIZE}px for visibility.")
    print("Open these images to visually check the model is focusing on")
    print("sensible regions (e.g. facial/texture areas) rather than random")
    print("background noise.")