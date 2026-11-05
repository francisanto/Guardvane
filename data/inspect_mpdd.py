import os
import kagglehub

# Download / locate MPDD
path = kagglehub.dataset_download(
    "mohammedaminejebbar/malicious-prompt-detection-dataset-mpdd"
)

print("\nDataset location:")
print(path)

print("\nFiles found:")
for root, dirs, files in os.walk(path):
    for file in files:
        print(os.path.join(root, file))