import torch
import torch.nn as nn
import os

class DummyDeepfakeViT(nn.Module):
    def __init__(self):
        super().__init__()
        # Simple conv network to take (1, 3, 224, 224) and output (1, 2)
        # using some large strides so it's super fast and tiny
        self.conv1 = nn.Conv2d(3, 8, kernel_size=16, stride=16) # (1, 8, 14, 14)
        self.conv2 = nn.Conv2d(8, 2, kernel_size=14, stride=1) # (1, 2, 1, 1)

    def forward(self, pixel_values):
        x = self.conv1(pixel_values)
        x = torch.relu(x)
        x = self.conv2(x)
        return x.view(-1, 2)

model = DummyDeepfakeViT()
# set deterministic weights for the mock so it behaves consistently
torch.manual_seed(42)
nn.init.normal_(model.conv1.weight, mean=0.1, std=0.5)
nn.init.normal_(model.conv2.weight, mean=0.1, std=0.5)

dummy_input = torch.randn(1, 3, 224, 224)
os.makedirs("models", exist_ok=True)
torch.onnx.export(
    model, 
    dummy_input, 
    "models/deepfake_vit.onnx", 
    input_names=["pixel_values"], 
    output_names=["logits"],
    opset_version=14
)
print("Successfully generated mock models/deepfake_vit.onnx")
