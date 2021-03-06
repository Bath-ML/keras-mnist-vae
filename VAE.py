# # Imports
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np
import tensorflow as tf
import tensorflow.contrib.distributions as dis
from keras import backend as K
from keras.layers import Input, Dense, Lambda, Layer
from keras.models import Model
from keras import metrics
from keras.datasets import mnist
from scipy.stats import norm

# # Variational autoencoder (VAE)
Normal = tf.contrib.distributions.Normal
t = dis.kl(Normal(3.0, 2.0), Normal(0.0, 1.0)) #mean, st dev
t2  =  dis.kl(Normal(3.0, 1.0), Normal(2.9,1.0))
t3 =  dis.kl(Normal(3.0, 1.0), Normal(3.0,1.0))

with tf.Session() as session:
    t_val = session.run(t)
    print ('KLD(N(3,2), N(0,1)) =', t_val, ", value = ", .5*(np.log(2)  - 1  + 2.0 + 3**2 ))
    t_val = session.run(t2)
    print('KLD(N(3,1), N(2.9,1)) =', t_val)
    t_val = session.run(t3)
    print('KLD(N(3,1), N(3,1)) =', t_val)

# # Implementing the variational auto encoder

#hyper parameters
batch_size = 200
latent_dim = 2
intermediate_dim = 625
epochs = 20                     #150
epsilon_std = 1.0
original_dim = 784
x = Input(shape=(original_dim,))
h = Dense(intermediate_dim, activation='relu')(x) #relu

#latent variables
z_mean = Dense(latent_dim)(h)
z_log_var = Dense(latent_dim)(h)

def sampling(args):
    z_mean, z_log_var = args
    epsilon = K.random_normal(shape=(K.shape(z_mean)[0], latent_dim), mean=0.,
                              stddev=epsilon_std)
    return z_mean + K.exp(z_log_var / 2) * epsilon

z = Lambda(sampling, output_shape=(latent_dim,))([z_mean, z_log_var])

decoder_h = Dense(intermediate_dim, activation='relu')
decoder_mean = Dense(original_dim, activation='sigmoid')
h_decoded = decoder_h(z)
x_decoded_mean = decoder_mean(h_decoded)

# Custom loss layer
class CustomVariationalLayer(Layer):
    def __init__(self, **kwargs):
        self.is_placeholder = True
        super(CustomVariationalLayer, self).__init__(**kwargs)

    def vae_loss(self, x, x_decoded_mean):
        xent_loss = original_dim * metrics.binary_crossentropy(x, x_decoded_mean)
        kl_loss = - 0.5 * K.sum(1 + z_log_var - K.square(z_mean) - K.exp(z_log_var), axis=-1)
        return K.mean(xent_loss + kl_loss)

    def call(self, inputs):
        x = inputs[0]
        x_decoded_mean = inputs[1]
        loss = self.vae_loss(x, x_decoded_mean)
        self.add_loss(loss, inputs=inputs)
        # We won't actually use the output.
        return x

y = CustomVariationalLayer()([x, x_decoded_mean])
vae = Model(x, y)
vae.compile(optimizer='rmsprop', loss=None)

# train the VAE on MNIST digits
(x_train, y_train), (x_test, y_test) = mnist.load_data()
x_train = x_train.astype('float32') / 255.
x_test = x_test.astype('float32') / 255.
x_train = x_train.reshape((len(x_train), np.prod(x_train.shape[1:])))
x_test = x_test.reshape((len(x_test), np.prod(x_test.shape[1:])))

history = vae.fit(x_train,
        shuffle=True,
        epochs=epochs,
        batch_size=batch_size,
        validation_data=(x_test, None))

encoder = Model(x, z_mean)

# plot history for loss
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend(['train', 'validation'], loc='upper right')

# display a 2D plot of the digit classes in the latent space
x_test_encoded = encoder.predict(x_test, batch_size=batch_size)
plt.figure(figsize=(8, 8))
colors = cm.rainbow(np.linspace(0, 1, len(set(y_test))))
colors = colors[np.asarray(y_test)]
plt.scatter(x_test_encoded[:, 0], x_test_encoded[:, 1], c=colors)
plt.xlabel("$\mu$")
plt.ylabel("$\log(\Sigma)$")
m = cm.ScalarMappable(cmap=cm.jet)
m.set_array(colors)
plt.colorbar(m)

# build a digit generator that can sample from the learned distribution
decoder_input = Input(shape=(latent_dim,))
_h_decoded = decoder_h(decoder_input)
_x_decoded_mean = decoder_mean(_h_decoded)
generator = Model(decoder_input, _x_decoded_mean)

# display a 2D manifold of the digits
n = 15  # figure with 15x15 digits
digit_size = 28
figure = np.zeros((digit_size * n, digit_size * n))
grid_x = norm.ppf(np.linspace(0.05, 0.95, n))
grid_y = norm.ppf(np.linspace(0.05, 0.95, n))

for i, yi in enumerate(grid_x):
    for j, xi in enumerate(grid_y):
        z_sample = np.array([[xi, yi]])
        x_decoded = generator.predict(z_sample)
        digit = x_decoded[0].reshape(digit_size, digit_size)
        figure[i * digit_size: (i + 1) * digit_size,
               j * digit_size: (j + 1) * digit_size] = digit

plt.figure(figsize=(10, 10))
plt.imshow(figure, cmap='Greys_r')
