from tensorflow import keras
from tensorflow.keras import layers
from mlflow import log_metric
import gzip, pickle, os
import numpy as np
import tensorflow as tf

batch_size = 128
epochs = int(os.getenv("EPOCHS","5"))
print ("Number of epochs:", epochs)
num_classes = 10
input_shape = (28, 28, 1)
MODEL_DIR = "/opt/dkube/output/"

#load dataset
f = gzip.open('/mnist/mnist.pkl.gz', 'rb')
data = pickle.load(f, encoding='bytes')
f.close()
(x_train, y_train), (x_test, y_test) = data

# Scale images to the [0, 1] range
x_train = x_train.astype("float32") / 255
x_test = x_test.astype("float32") / 255
# Make sure images have shape (28, 28, 1)
x_train = np.expand_dims(x_train, -1)
x_test = np.expand_dims(x_test, -1)
print("x_train shape:", x_train.shape)
print(x_train.shape[0], "train samples")
print(x_test.shape[0], "test samples")


# convert class vectors to binary class matrices
y_train = keras.utils.to_categorical(y_train, num_classes)
y_test = keras.utils.to_categorical(y_test, num_classes)

# Network
model = keras.Sequential(
    [
        keras.Input(shape=input_shape),
        layers.Conv2D(32, kernel_size=(3, 3), activation="relu"),
        layers.MaxPooling2D(pool_size=(2, 2)),
        layers.Conv2D(64, kernel_size=(3, 3), activation="relu"),
        layers.MaxPooling2D(pool_size=(2, 2)),
        layers.Flatten(),
        layers.Dropout(0.5),
        layers.Dense(num_classes, activation="softmax"),
    ]
)

# mlflow metric logging
class loggingCallback(keras.callbacks.Callback):
    def on_epoch_end(self, epoch, logs=None):
        accuracy_metric = "accuracy"
        if "acc" in logs:
            accuracy_metric = "acc"

        log_metric ("train_loss", logs["loss"], step=epoch)
        log_metric ("train_accuracy", logs[accuracy_metric], step=epoch)
        log_metric ("val_loss", logs["val_loss"], step=epoch)
        log_metric ("val_accuracy", logs["val_" + accuracy_metric], step=epoch)


model.compile(loss="categorical_crossentropy", optimizer="adam", metrics=["accuracy"])

model.fit(x_train, y_train, batch_size=batch_size, epochs=epochs, verbose=0, validation_split=0.1, 
        callbacks=[loggingCallback(), tf.keras.callbacks.TensorBoard(log_dir=MODEL_DIR)])
        
export_path = MODEL_DIR
version = 0
if not tf.io.gfile.exists(export_path):
    tf.io.gfile.makedirs(export_path)
model_contents = tf.io.gfile.listdir(export_path)

saved_models = []
for mdir in model_contents:
    if mdir != 'logs' and mdir != 'metrics'and mdir != 'weights.h5':
        saved_models.append(int(mdir))
if len(saved_models) < 1:
    version = 1
else:
    version = max(saved_models) + 1
model.save(export_path + 'weights.h5')
tf.keras.backend.set_learning_phase(0)  # Ignore dropout at inference
tf.saved_model.save(model,export_path + str(version))
print("Model saved, version = ", version)
