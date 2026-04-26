from flask import Flask, request, jsonify
import numpy as np
import time
import psutil
import os

app = Flask(__name__)

def get_system_metrics():
    """Get current CPU and memory usage"""
    process = psutil.Process(os.getpid())
    return {
        'cpu_percent': process.cpu_percent(interval=0.1),
        'memory_mb': process.memory_info().rss / 1024 / 1024,
    }

@app.route('/compute/matmul', methods=['POST'])
def matrix_multiply():
    """
    Heavy CPU computation: Matrix multiplication
    Expected JSON: {"size": 2000}
    """
    data = request.json
    size = data.get('size', 1000)

    if size < 1 or size > 5000:
        return jsonify({'error': 'Size must be between 1 and 5000'}), 400

    start_time = time.time()
    start_metrics = get_system_metrics()

    # Create random matrices
    A = np.random.rand(size, size)
    B = np.random.rand(size, size)

    # Perform matrix multiplication (heavy CPU work)
    C = np.matmul(A, B)

    end_time = time.time()
    end_metrics = get_system_metrics()

    return jsonify({
        'operation': 'matrix_multiplication',
        'matrix_size': size,
        'computation_time_seconds': round(end_time - start_time, 4),
        'cpu_usage_percent': round(end_metrics['cpu_percent'], 2),
        'memory_used_mb': round(end_metrics['memory_mb'], 2),
        'result_shape': str(C.shape),
    }), 200

@app.route('/compute/matinv', methods=['POST'])
def matrix_inverse():
    """
    Heavy CPU computation: Matrix inversion
    Expected JSON: {"size": 1000}
    """
    data = request.json
    size = data.get('size', 500)

    if size < 1 or size > 3000:
        return jsonify({'error': 'Size must be between 1 and 3000'}), 400

    start_time = time.time()
    start_metrics = get_system_metrics()

    # Create random invertible matrix
    A = np.random.rand(size, size)

    # Perform matrix inversion (heavy CPU work)
    A_inv = np.linalg.inv(A)

    end_time = time.time()
    end_metrics = get_system_metrics()

    return jsonify({
        'operation': 'matrix_inversion',
        'matrix_size': size,
        'computation_time_seconds': round(end_time - start_time, 4),
        'cpu_usage_percent': round(end_metrics['cpu_percent'], 2),
        'memory_used_mb': round(end_metrics['memory_mb'], 2),
        'result_shape': str(A_inv.shape),
    }), 200

@app.route('/compute/eigenvalues', methods=['POST'])
def eigenvalue_decomposition():
    """
    Heavy CPU computation: Eigenvalue decomposition
    Expected JSON: {"size": 1000}
    """
    data = request.json
    size = data.get('size', 1000)

    if size < 1 or size > 3000:
        return jsonify({'error': 'Size must be between 1 and 3000'}), 400

    start_time = time.time()
    start_metrics = get_system_metrics()

    # Create random symmetric matrix (guaranteed to have real eigenvalues)
    A = np.random.rand(size, size)
    A = (A + A.T) / 2

    # Perform eigenvalue decomposition (heavy CPU work)
    eigenvalues, eigenvectors = np.linalg.eig(A)

    end_time = time.time()
    end_metrics = get_system_metrics()

    return jsonify({
        'operation': 'eigenvalue_decomposition',
        'matrix_size': size,
        'computation_time_seconds': round(end_time - start_time, 4),
        'cpu_usage_percent': round(end_metrics['cpu_percent'], 2),
        'memory_used_mb': round(end_metrics['memory_mb'], 2),
        'num_eigenvalues': len(eigenvalues),
    }), 200

@app.route('/compute/fft', methods=['POST'])
def fast_fourier_transform():
    """
    Heavy CPU computation: Fast Fourier Transform
    Expected JSON: {"size": 1000000}
    """
    data = request.json
    size = data.get('size', 100000)

    if size < 1 or size > 10000000:
        return jsonify({'error': 'Size must be between 1 and 10000000'}), 400

    start_time = time.time()
    start_metrics = get_system_metrics()

    # Create random signal
    signal = np.random.rand(size)

    # Perform FFT (heavy CPU work)
    fft_result = np.fft.fft(signal)

    end_time = time.time()
    end_metrics = get_system_metrics()

    return jsonify({
        'operation': 'fast_fourier_transform',
        'signal_size': size,
        'computation_time_seconds': round(end_time - start_time, 4),
        'cpu_usage_percent': round(end_metrics['cpu_percent'], 2),
        'memory_used_mb': round(end_metrics['memory_mb'], 2),
        'result_size': len(fft_result),
    }), 200

@app.route('/health', methods=['GET'])
def health():
    metrics = get_system_metrics()
    return jsonify({
        'status': 'healthy',
        'cpu_percent': round(metrics['cpu_percent'], 2),
        'memory_mb': round(metrics['memory_mb'], 2),
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5001)
