import numpy as np
import pandas as pd
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler 
from data.vantage_loader import fetch_stocks


scaler= StandardScaler()

class PredictionModel (nn.Module):
          def __init__(self,input_dim,hidden_dim,num_layers,output_dim):
            super(PredictionModel,self).__init__()
            self.num_layers = num_layers
            self.hidden_dim= hidden_dim
            self.lstm =nn.LSTM(input_dim,hidden_dim,num_layers,batch_first=True)
            self.fc=nn.Linear(hidden_dim,output_dim)

          def forward(self,x):
            h0= torch.zeros(self.num_layers,x.size(0),self.hidden_dim,device=device)
            c0= torch.zeros(self.num_layers,x.size(0),self.hidden_dim,device=device)

            out,(hn,cn)  =self.lstm(x,(h0.detach(),c0.detach()))
            out= self.fc(out[:,-1,:])
            return out
          

model= PredictionModel(input_dim=1,hidden_dim=32,num_layers=4,output_dim=1)
checkpoint = torch.load("prediction_model/model_after_RUMOF.pth", map_location=torch.device('cpu'))
model.load_state_dict(checkpoint['model_state_dict'])
model.eval()

device = torch.device('cpu')
model.to(device)
results = []


def predict_next_price():
    with torch.no_grad():
        pip=0
        print("🚀 Starting price predictions...")
        for stock in fetch_stocks():
            pip+=1
            df = yf.download(stock, period="40d", interval="1d")
            if len(df) < 30:
                continue
            window = df[-30:]['Close'].values.reshape(-1, 1)
            window_scaled = scaler.fit_transform(window)
            X_input = np.expand_dims(window_scaled, axis=0)
            X_tensor = torch.tensor(X_input, dtype=torch.float32).to(device)
            prediction = model(X_tensor)
            predicted_price_scaled = prediction.cpu().numpy().flatten()
            predicted_price = scaler.inverse_transform(predicted_price_scaled.reshape(-1, 1))

            print(f'processing ticker {pip} : {stock} predicted price: {predicted_price[0][0]}')
            results.append(
                {
                    'Stock': stock,
                    'Predicted_Price': predicted_price[0][0]
                }
            )
        Price_Predictions = pd.DataFrame(results)
        Price_Predictions.to_csv('prediction_model/price_predictions.csv', index=False)
        print(Price_Predictions)


