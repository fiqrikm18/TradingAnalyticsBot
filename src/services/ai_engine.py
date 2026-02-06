import os
import logging
import numpy as np
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from config.settings import MODEL_PATH, LOOKBACK_DAYS


def create_lstm_model(input_shape):
    """Builds the LSTM model structure."""
    model = Sequential([
        Input(shape=input_shape),
        # 1. Feature Extraction (Wyckoff Patterns)
        LSTM(units=50, return_sequences=True),
        Dropout(0.2),

        # 2. Pattern Recognition
        LSTM(units=50, return_sequences=False),
        Dropout(0.2),

        # 3. Decision Layer
        Dense(units=25, activation='relu'),
        Dense(units=1, activation='sigmoid')  # Output: 0-1 Confidence
    ])
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model


def train_model():
    """Trains a fresh LSTM model (Synthetic Data for Demo)."""
    logging.info("Training synthetic LSTM model...")

    # Generate Smart Synthetic Wyckoff Data
    # Class 1: ACCEPT (Uptrend, Sideways, Breakout, AND CHOPPY/VOLATILE)
    # Class 0: REJECT (Falling Knife Only)

    num_samples = 1000
    X_train = np.zeros((num_samples, LOOKBACK_DAYS, 5))
    y_train = np.zeros(num_samples)

    for i in range(num_samples):
        if i % 2 == 0:
            # Class 1: ACCEPT EVERYTHING EXCEPT CRASHES
            y_train[i] = 1

            # Mixture: All positive biased patterns
            # Even "Sideways" with High Noise (0.25) is now Class 1
            pattern_type = np.random.choice(
                ['breakout', 'markup', 'sideways', 'messy_up'])

            # High Noise Tolerance
            noise_level = np.random.uniform(0.1, 0.3)

            if pattern_type == 'breakout':
                split = int(LOOKBACK_DAYS * 0.7)
                sideways = np.random.normal(0, noise_level, split)
                breakout = np.linspace(
                    0, 0.5, LOOKBACK_DAYS - split) + sideways[-1]
                trend = np.concatenate([sideways, breakout])

            elif pattern_type == 'markup':
                trend = np.linspace(0, 0.8, LOOKBACK_DAYS)
                trend += np.random.normal(0, noise_level, LOOKBACK_DAYS)

            elif pattern_type == 'sideways':
                # Accumulation with HIGH noise is fine
                trend = np.random.normal(0, noise_level, LOOKBACK_DAYS)

            else:  # messy_up
                steps = np.random.normal(
                    0.1, 1.5, LOOKBACK_DAYS)  # High variance up
                trend = np.cumsum(steps)

            # Add to features
            for f in range(5):
                if pattern_type == 'messy_up':
                    rw = trend
                    rw = (rw - rw.min()) / (rw.max() - rw.min() + 1e-6)
                    X_train[i, :, f] = rw
                else:
                    X_train[i, :, f] = trend + \
                        np.random.normal(0, 0.05, LOOKBACK_DAYS)

        else:
            # Class 0: REJECTION (Falling Knives ONLY)
            y_train[i] = 0

            neg_type = np.random.choice(['downtrend', 'crash'])

            if neg_type == 'downtrend':
                # Steady Downtrend
                trend = np.linspace(0, -1, LOOKBACK_DAYS)
                noise = np.random.normal(0, 0.15, LOOKBACK_DAYS)
                feat_data = trend + noise

            else:  # crash
                # Extreme Drop
                trend = np.linspace(0, -2, LOOKBACK_DAYS)
                noise = np.random.normal(0, 0.2, LOOKBACK_DAYS)
                feat_data = trend + noise

            # Normalize 0-1
            f_min, f_max = feat_data.min(), feat_data.max()
            if f_max != f_min:
                feat_data = (feat_data - f_min) / (f_max - f_min)
            else:
                feat_data = np.zeros(LOOKBACK_DAYS)

            for f in range(5):
                X_train[i, :, f] = feat_data

    input_shape = (X_train.shape[1], X_train.shape[2])

    model = create_lstm_model(input_shape)
    model.fit(X_train, y_train, epochs=10, batch_size=32, verbose=0)

    # Save model
    try:
        model.save(MODEL_PATH)
        logging.info(f"Model saved to {MODEL_PATH}")
    except Exception as e:
        logging.error(f"Failed to save model: {e}")

    logging.info("Model training complete.")
    return model


def load_model():
    """Loads model from disk or returns None."""
    if os.path.exists(MODEL_PATH):
        try:
            logging.info(f"Loading model from {MODEL_PATH}...")
            return tf.keras.models.load_model(MODEL_PATH)
        except Exception as e:
            logging.error(f"Failed to load model: {e}")
            return None
    return None


def get_lstm_score(model, df):
    """Prepares data and predicts confidence score."""
    if len(df) < LOOKBACK_DAYS:
        return 0.0

    data = df[['Open', 'High', 'Low', 'Close', 'Volume']].values

    # Scale Data
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data)

    # Create Sequence
    X = []
    X.append(scaled_data[-LOOKBACK_DAYS:])
    X = np.array(X)

    # Predict
    prediction = model.predict(X, verbose=0)
    return float(prediction[0][0])
