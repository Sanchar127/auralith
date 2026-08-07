FROM python:3.12-slim

WORKDIR /workspace
ENV PYTHONPATH=/app/subscription/generated:/app/subscription
RUN pip install --no-cache-dir \
    grpcio \
    grpcio-tools \
    protobuf

CMD ["bash"]