# -*- coding: utf-8 -*-
"""movie_review_rating_prediction_using_LSTM_model

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/10RYbmSZ4-dEjY_qJwyHsZGE6ojjk4Wdy
"""

import torch
print(torch.__version__)
# 1.6.0이 안나온다면 아래 코드 실행 필요

!pip3 install torch==1.6.0+cu101 torchtext==0.7.0 -f https://download.pytorch.org/whl/torch_stable.html
# 1회만 실행할 것 
# 실행 후 런타임 재실행 필요

import torch, torchtext
print(torch.__version__)     # 1.6.0+cu101
print(torchtext.__version__) # 0.7.0

from google.colab import drive
drive.mount('/content/drive')

!cp drive/MyDrive/AI\ School/8주차/GoogleNews-vectors-negative300.bin.gz . #구글에서 학습을 미리 한 word2vec vector. cp(copy)
!gunzip GoogleNews-vectors-negative300.bin.gz #gz 파일의 압축 파일인데 gunzip으로 압축 파일을 압축해제한다.

import os
import collections #collections은 python의 내장 모듈로서 다양한 자료구조를 호출하여 사용할 수 있다. 
import nltk
nltk.download('punkt')
#This tokenizer divides a text into a list of sentences, by using an unsupervised algorithm to build a model for abbreviation words, collocations, and words that start sentences.
#The NLTK data package includes a pre-trained Punkt tokenizer for English.
import numpy as np
import torch.nn as nn
import torch.optim as optim
import tqdm.notebook as tqdm

from torch.utils.data import DataLoader, random_split #DataLoader가 하는 역할이 정확히 코드에서 뭘까? 
from torch.nn.utils.rnn import pack_padded_sequence, pad_sequence, pad_packed_sequence 
#pad_packed_sequence: pack_padded_sequence를 통해 하나로 쭈욱 이어진 문장을 LSTM에 넣어주면 아웃풋은 동일한 형태로 나오게 된다. 이 때 다시 pad_sequence를 통해 나온 형태로 문장을 쪼개주는 역할을 이 함수가 한다. 
#pad_sequence: 만약 batch_size가 5이라면 문장을 5개를 가지고 오는데 이 때 문장의 길이가 모두 다르다면 문장의 길이를 동일하게 해주기 위해서 pad를 넣어주는데 이때 사용하는 method가 pad_sequence이다.
#            : 참고로 길이가 가장 긴 문장이 표준이 된다. 
#pack_padded_sequence: pad_sequence를 사용해서 길이를 맞춘 batch를 한 줄로 쭈욱 이어주는 기능을 한다. 사전에 pad_sequence를 사용해서 길이를 맞춰주어야 한다. 
#질문: 강의 설명 중, pack_padded_sequence를 통해 한 줄로 이어준다고 하셨는데 그 때 pad는 없어지고 각 문장의 원래 길이가 이어지는 것처럼 설명을 하셨는데 그럼 pad_sequence과정이 왜 필요한 것인가요? 


from torchtext.experimental.vocab import Vocab
from torchtext.experimental.datasets.text_classification import IMDB

from gensim.models.keyedvectors import KeyedVectors

# 뉴럴 네트워크 하이퍼파라미터
num_classes = 2
num_epochs = 10
evaluate_per_steps = 150
learning_rate = 0.0001 #dev accuracy가 변동성이 심하면 learning_rate를 조금 더 작게 한다. 
dropout_rate = 0.2
batch_size = 50 #학습을 빨리 진행하게 하기 위해서 키워주면 된다. 
weight_decay = 5e-4

# Text LSTM 하이퍼파라미터
embedding_dim = 300 #구글의 word2vec vector 차원이기에 바꾸면 안된다. 
hidden_size = 300 #이걸 크게 하면 lstm의 표현력이 증가된다. 
use_only_last = False #모든 hidden state vector를 사용할지 안할지를 결정하는 파라미터, False일 때 전체 사용.

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(device)

class TextLSTM(nn.Module):
    def __init__(self, num_classes, vocab_size, embedding_dim, pretrained_embedding, hidden_size, dropout_rate, use_only_last=True):
        super().__init__()
        self.embedding = nn.Embedding(num_embeddings=vocab_size, embedding_dim=embedding_dim)
        self.embedding.weight.detach().copy_(torch.tensor(pretrained_embedding))
        self.lstm = nn.LSTM(input_size=embedding_dim, hidden_size=hidden_size, bidirectional=True) #bidirectional 옵션 적용 
        self.dropout = nn.Dropout(dropout_rate)
        self.fc = nn.Linear(in_features=hidden_size*2, out_features=num_classes) # 2 : bidirection으로 차원이 2배 늘어남 
        self.use_only_last = use_only_last

    def forward(self, text, length):
        # layer : stacked LSTM을 사용하는 경우, 기본값 : 1 , nn.LSTM에 인수로 num_layers=2 or 3 .. 을 넣으면 사용하는 LSTM의 층수가 바뀐다. 이때 layer는 stack되면 값이 그에 따라 바뀐다. 
        # direction : bidirectional LSTM을 사용하는 경우(2), 기본값 : 1(사용 안함)
        batch_size = length.size(0)
        out = self.embedding(text) # [T, Batch, embedding] , T : longest sentence length 
        out = pack_padded_sequence(out, lengths=length, enforce_sorted=False) # [SL, embedding] , SL : Total Sequence Length
        all, (h, c) = self.lstm(out) # all : [SL, hidden * layer * direction] hidden은 lstm을 통해 나온 값의 size 
                                     # h   : [layer * direction, batch, hidden_size] bidirection이니깐 2, batch 사이즈만큼의 문장을 가지고 있고, 마지막 그 hidden size 
                                     # c   : [layer * direction, batch, hidden_size]
        #self.lstm(out)을 통해 모든 hidden state, 마지막 hidden state 그리고 cell state가 결과로 나온다. cell state도 맨 마지막에 정리된 state. 
        i_all, i_length = pad_packed_sequence(all) # i_all    : [T, Batch, hidden * layer * direction] 
                                                   # i_length : length랑 똑같음 
        if self.use_only_last : 
            ## 모든 hidden을 사용하는 경우, 모든 hidden state를 가지고 와서 평균을 내서 사용. 
            out = torch.mean(i_all, dim=0)    # [batch, hidden_size * layer * direction] dim을 0으로 한 이유는 T라는 위치로 평균을 냈으니깐 T가 0의 위치에 있으니깐 dim=0으로 한다.

        else : 
            ## 마지막 hidden만 사용하는 경우 
            out = h.permute((1, 0, 2))        # [batch, layer * direction, hidden_size] / 모든 forward의 처음은 batch가 먼저 왔기 때문에 순서를 조금 변경해줘야 한다. 
            #permute를 사용하면 index의 위치를 바꿀수 있다. 
            out = out.reshape(batch_size, -1) # [batch, hidden_size * layer * direction] #fully connected하기 위해 shape을 바꿔주는데, 이 때 reshape을 사용하고 batch 사이즈를 제외하고 
                                              # 나머지를 곱해서 shape을 바꿔준다. 

        out = self.dropout(out)
        out = self.fc(out)
        return out

# batch:
# [
#   (tensor(0 or 1), tensor([3, 4, 13, 38, 20]),    5 단어
#   (tensor(0 or 1), tensor([21, 21, 3, 76]),       4 단어
#   (tensor(0 or 1), tensor([53, 48, 1]),           3 단어
#   (tensor(0 or 1), tensor([3, 4, 4, 1, 3, 20]),   6 단어
# ]

def collate(batch):
    labels, text = zip(*batch)

    lengths = []
    for t in text:
        lengths.append(len(t))

    text = pad_sequence(text) # 가장 긴 text를 기준으로 직사각형으로 만들어 줌
    lengths = torch.tensor(lengths) # List to tensor
    labels = torch.stack(labels) # stack : 1개의 차원을 추가해주면서 합치는 것 / 0 dim -> 1 dim(tensor)
    return labels, text, lengths

def evaluate(model, data_loader):
    with torch.no_grad():
        model.eval()
        num_corrects = 0
        num_total = 0
        for label, text, length in data_loader:
            label = label.to(device)
            text = text.to(device)
            length = length.to(device)

            output = model(text, length)
            predictions = output.argmax(dim=-1)
            num_corrects += (predictions == label).sum().item()
            num_total += label.size(0)
            
        return num_corrects / num_total

def get_pre_trained_emb(vocab, embedding_dim, pre_trained_path):
    print('start to load google word2vec model')
    google_word2vec = KeyedVectors.load_word2vec_format(pre_trained_path, binary=True)#, limit=60000)
    print('Done!')

    matrix_len = len(vocab)
    weights_matrix = np.zeros((matrix_len, embedding_dim))
    words_found = 0

    for i, word in enumerate(vocab.itos): # itos : Index TO String
        try: 
            weights_matrix[i] = google_word2vec[word]
            words_found += 1
        except KeyError:
            weights_matrix[i] = np.random.uniform(-0.2, 0.2, size=google_word2vec.vector_size)

    print(f'total vocab length : {matrix_len}, matched word count : {words_found}')
    return weights_matrix

# 데이터 준비 
train_dataset, test_dataset = IMDB(tokenizer=None, data_select=("train", "test"))

vocab = train_dataset.get_vocab()
num_train = int(len(train_dataset)*0.9)
num_dev = len(train_dataset) - num_train

train_dataset, dev_dataset = random_split(train_dataset, (num_train, num_dev))
print(f'dataset size train / dev / test : {len(train_dataset)} / {len(dev_dataset)} / {len(test_dataset)}')

train_loader = DataLoader(train_dataset, batch_size=batch_size    , num_workers=8, collate_fn=collate)
dev_loader   = DataLoader(dev_dataset,   batch_size=batch_size * 4, num_workers=8, collate_fn=collate)
test_loader  = DataLoader(test_dataset,  batch_size=batch_size * 4, num_workers=8, collate_fn=collate)

# pre trained word embedding : Google word2vec 
vectors = get_pre_trained_emb(vocab=vocab, 
                              embedding_dim=embedding_dim, 
                              pre_trained_path='GoogleNews-vectors-negative300.bin')

# 1. 모든 hidden 사용. mean 이용 
# 모델 선언 
model = TextLSTM(num_classes=num_classes,
                 embedding_dim=embedding_dim,
                 vocab_size=len(vocab),
                 pretrained_embedding=vectors,
                 hidden_size=hidden_size,
                 dropout_rate=dropout_rate,
                 use_only_last=use_only_last).to(device)

# 로스, 옵티마이저 정의
optimizer = optim.Adam(model.parameters(), learning_rate, weight_decay=weight_decay)
criterion = nn.CrossEntropyLoss()

# 학습 진행 
steps = 0
max_dev_accuracy = 0.0
import tqdm.notebook as tqdm
for epoch in tqdm.trange(num_epochs):
    progress = tqdm.tqdm(train_loader)
    for label, text, length in progress:
        model.train()
        steps += 1
        label = label.to(device)
        text = text.to(device)
        length = length.to(device)

        output = model(text, length)
        loss = criterion(output, label)
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        progress.set_description(f'train loss: {loss.item():.4f}')

        if steps % evaluate_per_steps == 0:
            print('***** evaluating on the dev set *****')
            dev_accuracy = evaluate(model, dev_loader)
            print(f'dev accuracy: {dev_accuracy:.4f}')
            if dev_accuracy > max_dev_accuracy:
                max_dev_accuracy = dev_accuracy
                print('achieve dev-best accuracy. saving.')
                torch.save(model.state_dict(), 'best_weight.pt')

# 평가
print('***** evaluating dev-best on the test set *****')
model.load_state_dict(torch.load('best_weight.pt'))
test_accuracy = evaluate(model, test_loader)
print(f'test accuracy: {test_accuracy}')

# 2. 마지막 hidden만 사용 
# 모델 선언 
model = TextLSTM(num_classes=num_classes,
                 embedding_dim=embedding_dim,
                 vocab_size=len(vocab),
                 pretrained_embedding=vectors,
                 hidden_size=hidden_size,
                 dropout_rate=dropout_rate,
                 use_only_last=True).to(device)

# 로스, 옵티마이저 정의
optimizer = optim.Adam(model.parameters(), learning_rate, weight_decay=weight_decay)
criterion = nn.CrossEntropyLoss()

# 학습 진행 
steps = 0
max_dev_accuracy = 0.0

import tqdm.notebook as tqdm
for epoch in tqdm.trange(num_epochs):
    progress = tqdm.tqdm(train_loader)
    for label, text, length in progress:
        print(label,text,length)
        assert()
        model.train()
        steps += 1
        label = label.to(device)
        text = text.to(device)
        length = length.to(device)

        output = model(text, length)
        loss = criterion(output, label)
        
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        progress.set_description(f'train loss: {loss.item():.4f}')

        if steps % evaluate_per_steps == 0:
            print('***** evaluating on the dev set *****')
            dev_accuracy = evaluate(model, dev_loader)
            print(f'dev accuracy: {dev_accuracy:.4f}')
            if dev_accuracy > max_dev_accuracy:
                max_dev_accuracy = dev_accuracy
                print('achieve dev-best accuracy. saving.')
                torch.save(model.state_dict(), 'best_weight.pt')

# 평가
print('***** evaluating dev-best on the test set *****')
model.load_state_dict(torch.load('best_weight.pt'))
test_accuracy = evaluate(model, test_loader)
print(f'test accuracy: {test_accuracy}')

# 평가
print('***** evaluating dev-best on the test set *****')
model.load_state_dict(torch.load('best_weight.pt'))
test_accuracy = evaluate(model, test_loader)
print(f'test accuracy: {test_accuracy}')

string = 'The quick brown fox jumps over the lazy dog'
count = 0 
print(len(string))
for i in range(len(string)):
  count += 1 
print(count)

from tqdm.notebook import tqdm 
import time
a=10
b=20
c=30
for i in tqdm(range(10)):
  print(i)
  time.sleep(0.5)
  i+=i
  print(i)
#   for e,f,g in tqdm(a,b,c):
#     print(e,f,g)
# # print(i)

type(train_loader)
