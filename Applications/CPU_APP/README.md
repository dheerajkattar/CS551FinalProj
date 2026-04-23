# CPU-Intensive Application

A Flask application that performs heavy CPU-bound computations via HTTP requests. Useful for testing autoscaling, load balancing, and resource management in cloud environments.

## Setup

```bash
pip install -r requirements.txt
python main.py
```

The API runs on `http://localhost:5001`

## CPU-Intensive Endpoints

### Matrix Multiplication
```bash
curl -X POST http://localhost:5001/compute/matmul \
  -H "Content-Type: application/json" \
  -d '{"size": 2000}'
```

**Parameters:**
- `size`: Matrix dimensions (size × size). Default: 1000. Max: 5000
- Multiplies two random matrices of specified size

### Matrix Inversion
```bash
curl -X POST http://localhost:5001/compute/matinv \
  -H "Content-Type: application/json" \
  -d '{"size": 1000}'
```

**Parameters:**
- `size`: Matrix dimensions. Default: 500. Max: 3000
- Inverts a random matrix using LU decomposition

### Eigenvalue Decomposition
```bash
curl -X POST http://localhost:5001/compute/eigenvalues \
  -H "Content-Type: application/json" \
  -d '{"size": 1000}'
```

**Parameters:**
- `size`: Matrix dimensions. Default: 1000. Max: 3000
- Decomposes a random symmetric matrix into eigenvalues/eigenvectors

### Fast Fourier Transform (FFT)
```bash
curl -X POST http://localhost:5001/compute/fft \
  -H "Content-Type: application/json" \
  -d '{"size": 1000000}'
```

**Parameters:**
- `size`: Signal size. Default: 100000. Max: 10000000
- Performs 1D FFT on a random signal

### Health Check
```bash
curl http://localhost:5001/health
```

## Response Format

All computation endpoints return:
```json
{
  "operation": "matrix_multiplication",
  "matrix_size": 2000,
  "computation_time_seconds": 12.34,
  "cpu_usage_percent": 85.5,
  "memory_used_mb": 256.7,
  "result_shape": "(2000, 2000)"
}
```

## Load Testing Example

```bash
# Test with increasing matrix sizes
for size in 500 1000 1500 2000; do
  echo "Testing matmul with size=$size"
  curl -X POST http://localhost:5001/compute/matmul \
    -H "Content-Type: application/json" \
    -d "{\"size\": $size}"
  echo ""
done
```

## Cloud Deployment Tips

This app is designed to test:
- **Autoscaling**: High CPU usage triggers scaling
- **Load balancing**: Distribute requests across multiple instances
- **Resource management**: Monitor CPU and memory usage
- **Performance monitoring**: Track computation times

Deploy to:
- **AWS EC2** with Auto Scaling Group
- **AWS ECS/Fargate** with CPU-based scaling
- **GCP Compute Engine** with Instance Groups
- **GCP Cloud Run** (for serverless testing)
