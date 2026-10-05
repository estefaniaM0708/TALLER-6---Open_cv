# entrenar_modelo.py
# Entrena una CNN sobre MNIST y guarda el modelo junto a este archivo.
# Ejecutar UNA SOLA VEZ antes de usar reconocer_y_enviar.py (tarda unos minutos).
# Tomado del ejemplo de clase "10) Open_Cv/entrenar_modelo.py" (repositorio U_Militar).

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import tensorflow as tf

CARPETA = os.path.dirname(os.path.abspath(__file__))

# 1. Cargar MNIST (se descarga sola la primera vez, ~11 MB)
(x_train, y_train), (x_test, y_test) = tf.keras.datasets.mnist.load_data()

# 2. Normalizar y dar forma para la CNN (28x28x1)
x_train = (x_train / 255.0).reshape(-1, 28, 28, 1)
x_test = (x_test / 255.0).reshape(-1, 28, 28, 1)

# 3. Red convolucional
modelo = tf.keras.Sequential([
    tf.keras.Input(shape=(28, 28, 1)),
    tf.keras.layers.Conv2D(32, (3, 3), activation='relu'),
    tf.keras.layers.MaxPooling2D((2, 2)),
    tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
    tf.keras.layers.MaxPooling2D((2, 2)),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(128, activation='relu'),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.Dense(10, activation='softmax'),
])
modelo.compile(optimizer='adam',
               loss='sparse_categorical_crossentropy',
               metrics=['accuracy'])

# 4. Entrenar con aumento de datos (rotaciones y traslaciones leves)
datagen = tf.keras.preprocessing.image.ImageDataGenerator(
    rotation_range=10, width_shift_range=0.1,
    height_shift_range=0.1, zoom_range=0.1)

modelo.fit(datagen.flow(x_train, y_train, batch_size=32),
           epochs=10, validation_data=(x_test, y_test))

# 5. Guardar
ruta = os.path.join(CARPETA, 'modelo_mnist_cnn.h5')
modelo.save(ruta)
print("Modelo guardado en", ruta)
