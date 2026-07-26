# syntax=docker/dockerfile:1.7
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

USER root

ARG EHTIM_COMMIT=22ae35f307921a4d423aa69f6aed6e93a74ecbc0
ARG EHTIM_TREE_SHA256
ARG EHTIM_PATCH_SHA256

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       git \
       build-essential \
       gfortran \
       libfftw3-dev \
       libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

COPY explicit-linux-64.txt /tmp/explicit-linux-64.txt
COPY patches/ehtim-1.1.0-python3-parloop.patch /tmp/ehtim-1.1.0-python3-parloop.patch

RUN echo "${EHTIM_PATCH_SHA256}  /tmp/ehtim-1.1.0-python3-parloop.patch" | sha256sum --check - \
    && micromamba create --yes --name vajra --file /tmp/explicit-linux-64.txt \
    && micromamba clean --all --yes

RUN git clone --filter=blob:none https://github.com/achael/eht-imaging.git /tmp/eht-imaging \
    && git -C /tmp/eht-imaging checkout --detach "${EHTIM_COMMIT}" \
    && test "$(git -C /tmp/eht-imaging rev-parse HEAD)" = "${EHTIM_COMMIT}" \
    && git -C /tmp/eht-imaging archive --format=tar HEAD | sha256sum | grep -F "${EHTIM_TREE_SHA256}" \
    && git -C /tmp/eht-imaging apply --check /tmp/ehtim-1.1.0-python3-parloop.patch \
    && git -C /tmp/eht-imaging apply /tmp/ehtim-1.1.0-python3-parloop.patch \
    && micromamba run -n vajra python -m compileall -q /tmp/eht-imaging/ehtim \
    && micromamba run -n vajra python -m pip install --no-deps /tmp/eht-imaging \
    && rm -rf /tmp/eht-imaging

RUN micromamba run -n vajra python - <<'PY'
import pkg_resources
import ehtim
import numpy
import scipy
import astropy
print({
    "ehtim": pkg_resources.get_distribution("ehtim").version,
    "numpy": numpy.__version__,
    "scipy": scipy.__version__,
    "astropy": astropy.__version__,
})
PY

ENV PATH=/opt/conda/envs/vajra/bin:/opt/conda/bin:$PATH \
    MPLBACKEND=Agg \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    PYTHONHASHSEED=0

RUN useradd --create-home --uid 10001 vajra \
    && mkdir -p /workspace \
    && chown -R vajra:vajra /workspace

USER 10001:10001
WORKDIR /workspace

ENTRYPOINT []
CMD ["python", "-c", "import ehtim; print('vajra-m87-ehtim-ready')"]
