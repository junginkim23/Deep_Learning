# -*- coding: utf-8 -*-
"""Direct implementation of Resnet 101

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1BB8eFN7j7I1LIcIEGDaSg0kcY-vm3OpZ
"""

import torch
import torch.nn as nn

class BasicBlock(nn.Module):
    def __init__(self, in_channels, out_channels, downsample):
        super().__init__()
        self.downsample = downsample 
        self.sample_matching = False

        if self.downsample: 
          stride = 2 
          self.down_size_net = nn.Sequential(
              nn.Conv2d(in_channels=in_channels,out_channels=out_channels*4,stride=2,kernel_size=1,bias=False),
              nn.BatchNorm2d(out_channels*4)
          )
        else:
          stride = 1
          # if in_channels != out_channels * 4:
          self.sample_matching = True
          self.sample_match_net = nn.Sequential(
            nn.Conv2d(in_channels=in_channels,out_channels=out_channels * 4, stride=1,kernel_size=1,bias=False),
            nn.BatchNorm2d(out_channels * 4)
          )

        # 첫 번째 컨볼루션 (1x1, stride=1)
        self.conv1 = nn.Conv2d(in_channels=in_channels,out_channels=out_channels,kernel_size=1,stride=1,bias=False)  # TODO: !!!!!! 구현해 보세요 !!!!!
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU()

        # 두 번째 컨볼루션 (3x3, stride=2 or 1 -> downsample 여부에 따라 다름)
        self.conv2 = nn.Conv2d(in_channels=out_channels,out_channels=out_channels,kernel_size=3,stride=stride,padding=1,bias=False)  # TODO: !!!!!! 구현해 보세요 !!!!!
        self.bn2 = nn.BatchNorm2d(out_channels)

        # 세 번째 컨볼루션 (1x1, stride=1, out_channels=out_channels * 4)
        self.conv3 = nn.Conv2d(in_channels=out_channels,out_channels=out_channels * 4, kernel_size=1, stride=1,bias=False)  # TODO: !!!!!! 구현해 보세요 !!!!!
        self.bn3 = nn.BatchNorm2d(out_channels * 4)

    def forward(self, x):
        if self.downsample:
          skip = self.down_size_net(x)
        else:
          skip = x
        
        if self.sample_matching:
          skip = self.sample_match_net(skip)

        # 첫 번째 컨볼루션 & BatchNorm
        out = self.conv1(x)
        out = self.bn1(out)
        # relu
        out = self.relu(out)
        # 두 번째 컨볼루션 & BatchNorm
        out = self.conv2(out)
        out = self.bn2(out)
        # relu
        out = self.relu(out)
        # 세 번째 컨볼루션 & BatchNorm
        out = self.conv3(out)
        out = self.bn3(out)
        # downsample & skip 커넥션 & relu
        out = out + skip 
        out = self.relu(out)
        return out 


class ResNet101(nn.Module):
    def __init__(self, num_classes=10):
        super().__init__()

        # 도입부 
        self.conv1 = nn.Conv2d(in_channels=3, out_channels=64, kernel_size=7, stride=2, padding=3,
                               bias=False)  # 7x7 convolution
        self.bn1 = nn.BatchNorm2d(num_features=64)
        self.relu = nn.ReLU()
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)

        # 중간층 (layer1 : num_block 3 / layer2 : num_block 4 / layer3 : num_block 23 / layer4 : num_block 3)
        self.layer1 = self._make_layer(in_channels=64, out_channels=64, num_blocks=3)
        self.layer2 = self._make_layer(in_channels=64 * 4, out_channels=128, num_blocks=4, downsample=True)
        self.layer3 = self._make_layer(in_channels=128 * 4, out_channels=256, num_blocks=23, downsample=True)
        self.layer4 = self._make_layer(in_channels=256 * 4, out_channels=512, num_blocks=3, downsample=True)

        # 아웃풋
        self.adappool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(512 * 4, num_classes)

    def _make_layer(self, in_channels, out_channels, num_blocks, downsample=False):
        layers = []
        layers.append(BasicBlock(in_channels, out_channels, downsample))
        for _ in range(1, num_blocks):
            layers.append(BasicBlock(out_channels * 4, out_channels, downsample=False))
        return nn.Sequential(*layers)

    def forward(self, x):
        batch_size = x.shape[0]
        # 도입부 forward 
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.maxpool(out)

        # 중간층 forward 
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        

        # 아웃풋 forward
        out = self.adappool(out)
        out = out.view(batch_size, -1)
        out = self.fc(out)

        return out

import torch.nn.functional as F
import torchvision
import torchvision.transforms as transforms
import matplotlib.pyplot as plt

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Hyper-parameters 
num_classes = 10
num_epochs = 10
batch_size = 100
learning_rate = 0.001

# Data PreProcessing
transforms_train = transforms.Compose([
                        transforms.RandomCrop(32, padding=4),
                        transforms.RandomHorizontalFlip(),
                        transforms.ToTensor(),
                        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
                    ])
transforms_test = transforms.Compose([
                        transforms.ToTensor(),
                        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
                    ])

# 파이토치에서 제공하는 CIFAR10 dataset
train_dev_dataset = torchvision.datasets.CIFAR10(root='./data',train=True, 
                                            transform=transforms_train, download=True)
test_dataset = torchvision.datasets.CIFAR10(root='./data', train=False, 
                                            transform=transforms_test, download=True)
train_dataset, dev_dataset = torch.utils.data.random_split(train_dev_dataset, [45000, 5000])

# 배치 단위로 데이터를 처리해주는 Data loader
train_loader = torch.utils.data.DataLoader(dataset=train_dataset,
                                          batch_size=batch_size,
                                          shuffle=True)
dev_loader = torch.utils.data.DataLoader(dataset=dev_dataset, 
                                         batch_size=batch_size,
                                         shuffle=False)
test_loader = torch.utils.data.DataLoader(dataset=test_dataset,
                                         batch_size=batch_size,
                                         shuffle=False)

model = ResNet101(num_classes).to(device) # 모델을 지정한 device로 올려줌 

# ## torch vision의 내장 구현 resnet 활용하기 
# model = torchvision.models.resnet101(pretrained=True).to(device)
# num_ftrs = model.fc.in_features
# model.fc = nn.Linear(num_ftrs, num_classes)

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
# model.parameters -> 가중치 w들을 의미

def evaluation(data_loader):
    correct = 0
    total = 0
    for images, labels in data_loader:
        images = images.to(device) 
        labels = labels.to(device)
        outputs = model(images)
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()
    return correct/total

loss_arr = []
max = 0.0
total_step = len(train_loader)

for epoch in range(num_epochs):
    for i, (images, labels) in enumerate(train_loader):
        model.train()
        # Move tensors to the configured device
        images = images.to(device)
        labels = labels.to(device)
        # Forward pass
        outputs = model(images)
        loss = criterion(outputs, labels)
        # Backward and optimize
        optimizer.zero_grad() # iteration 마다 gradient를 0으로 초기화
        loss.backward() # 가중치 w에 대해 loss를 미분
        optimizer.step() # 가중치들을 업데이트

        if (i+1) % 150 == 0:
            loss_arr.append(loss)
            print('Epoch [{}/{}], Step [{}/{}], Loss: {:.4f}'
                    .format(epoch+1, num_epochs, i+1, total_step, loss.item()))
            with torch.no_grad():
                model.eval()
                acc = evaluation(dev_loader)
                if max < acc :
                    max = acc 
                    print("max dev accuracy: ", max)
                    torch.save(model.state_dict(), 'model.ckpt')

with torch.no_grad():
    last_acc = evaluation(test_loader)
    print('Last Accuracy of the network on the 10000 test images : {} %'.format(last_acc*100))

    model.load_state_dict(torch.load('model.ckpt'))
    best_acc = evaluation(test_loader)
    print('Best Accuracy of the network on the 10000 test images : {} %'.format(best_acc*100))

# Save the model checkpoint
plt.plot(loss_arr)
plt.show()