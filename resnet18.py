# -*- coding: utf-8 -*-
"""ResNet18

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1TZvGXMKYBQ0h_uyRMk-QwdyY-CANM4dN
"""

import torch
import torch.nn as nn

class BasicBlock(nn.Module):
  def __init__(self,in_channels,out_channels,down_size):
    super().__init__()
    self.down_size=down_size
    
    if self.down_size:
      stride = 2
      self.skip_net = nn.Conv2d(in_channels=in_channels,out_channels=out_channels,kernel_size=3,stride=stride,padding=1)
      self.skip_bn = nn.BatchNorm2d(num_features=out_channels) 
    else:
      stride = 1 

    self.conv1 = nn.Conv2d(in_channels=in_channels,out_channels=out_channels,kernel_size=3,stride=stride,padding=1)
    self.bn1 = nn.BatchNorm2d(num_features=out_channels)
    self.relu = nn.ReLU()

    self.conv2 = nn.Conv2d(in_channels=out_channels,out_channels=out_channels,kernel_size=3, stride=1, padding=1)
    self.bn2 = nn.BatchNorm2d(num_features=out_channels)


  def forward(self,x):
    skip = x 
    if self.down_size:
      skip = self.skip_net(skip)
      skip = self.skip_bn(skip)
    out = self.conv1(x)
    out = self.bn1(out)
    out = self.relu(out)
    out = self.conv2(out)
    out = self.bn2(out)
    out = self.relu(out)
    out = out + skip 
    return out


class ResNet18(nn.Module):
    def __init__(self, num_classes=10):
        super().__init__()
        # 도입부 
        self.conv1 = nn.Conv2d(in_channels=3,out_channels=64,kernel_size=7,padding=3,stride=2)
        self.bn1 = nn.BatchNorm2d(num_features=64)
        self.relu = nn.ReLU()
        self.maxpool = nn.MaxPool2d(kernel_size=3,stride=2,padding=1)

        # 중간층 (layer1 ~ layer4)
        #layer1
        self.layer1 = self.make_layer(in_channels=64,out_channels=64,num_basic_block=2,down_size=False)
        #layer2 
        self.layer2 = self.make_layer(in_channels=64,out_channels=128,num_basic_block=2,down_size=True) #weight, height를 1/2 -> down_size=True 
        #layer3
        self.layer3 = self.make_layer(in_channels=128,out_channels=256,num_basic_block=2,down_size=True)
        #layer4
        self.layer4 = self.make_layer(in_channels=256,out_channels=512,num_basic_block=2,down_size=True)
        
        # 아웃풋 
        self.avgpool = nn.AdaptiveAvgPool2d((1,1))
        self.fc = nn.Linear(in_features=512,out_features=num_classes)
      

    def make_layer(self,in_channels,out_channels,num_basic_block,down_size=False): 
      layer = []
      #첫 번째 basicblock
      layer.append(BasicBlock(in_channels,out_channels,down_size=down_size)) 
      for i in range(1,num_basic_block):
        #2번째 이상 basicblock 만들기 
        layer.append(BasicBlock(out_channels,out_channels,down_size=False))
      return nn.Sequential(*layer)

    def forward(self, x):
        batch_size = x.shape[0]
        # 도입부 forward 
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.maxpool(out)

        # print(out.size())
        # assert()
        # 중간층 forward 
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = self.avgpool(out)
        out = out.view(batch_size,-1)
        # print('out.view를 한 번 보자',out.size())
        out = self.fc(out)
        # print('layer2 output',out.size())
        # assert()
        # 아웃풋 forward

        return out

import torch.nn.functional as F
import torchvision
from torchvision import datasets
import torchvision.transforms as transforms
import matplotlib.pyplot as plt

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(device)

# Hyper-parameters 
num_classes = 10
num_epochs = 30
batch_size = 100 # 다른 숫자로 나눠 떨어지지 않아서, 확인하기 수월하다. 
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

print(len(train_dataset))

model = ResNet18(num_classes).to(device) # 모델을 지정한 device로 올려줌 

## torch vision의 내장 구현 resnet 활용하기 
# model = torchvision.models.resnet18(pretrained=True)
# num_ftrs = model.fc.in_features
# model.fc = nn.Linear(num_ftrs, num_classes)
# model = model.to(device)

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
        # print(outputs.size())
        loss = criterion(outputs, labels)
        # Backward and optimize
        optimizer.zero_grad() # iteration 마다 gradient를 0으로 초기화
        loss.backward() # 가중치 w에 대해 loss를 미분
        optimizer.step() # 가중치들을 업데이트

        if (i+1) % 150 == 0:
            loss_arr.append(loss)
            print('Epoch [{}/{}], Step [{}/{}], Loss: {:.4f}'
                    .format(epoch+1, num_epochs, i+1, total_step, loss.item())) #total_step -> iteration 
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

plt.plot(loss_arr)
plt.show()

#images.zip을 왼쪽 파일칸에 올리기 
#unzip 진행 
!unzip images.zipy

## Custom Data 이용하기 
images_folder = ['airplane', 'automobile', 'bird', 'cat', 'deer', 'dog', 'frog', 'horse', 'ship', 'truck']

def infer(model, dataloader):
    model.eval() #모델을 평가 모드로 바꿔준다. 드롭아웃 및 배치 정규화를 평가 모드로 설정 이것을 하지 않으면 추론 결과가 일관성 없게 나타난다. 
    for inputs, labels in dataloader:
        inputs = inputs.to(device)
        labels = labels.to(device)
        print('1',model(inputs).size())
        outputs = model(inputs).softmax(dim=1)
        print('2',outputs.size())
        for label, output in zip(labels, outputs):
          folder_index = label.item()
          max_prob = output.max().item()
          max_class = output.argmax().item()
          print('Label is {} and Model says it is {} with {:.1f}% probability'.format(images_folder[folder_index], 
                                                                                    images_folder[max_class], 
                                                                                    max_prob * 100))

## prepare model 
num_classes = 10
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

model = ResNet18(num_classes).to(device) 
model.load_state_dict(torch.load('model.ckpt'))

## prepare dataloader 
data_dir = 'images'
input_size = 32
data_transform = transforms.Compose([
        transforms.Resize((input_size, input_size)),
        transforms.ToTensor(),
        transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)) #사람이 보는 RGB의 값을 기계가 보기 쉬운 RGB의 값으로 변경해준다. 
    ])

image_dataset = datasets.ImageFolder(data_dir, data_transform)
dataloader = torch.utils.data.DataLoader(image_dataset, batch_size=2,shuffle=False)
infer(model, dataloader)

