FROM node:22-bookworm-slim@sha256:be979e5523c76fa4d5ca4ebd3099078f220aa47ec39c48ad5b5df9314debd6eb
ARG ORCA_VERSION=1.4.277
ARG ORCA_SHA256=cc0be421b6dc995e74c855db21d7f6c428ed759419d6a494c8ad08773812ea29
ARG APT_MIRROR=http://mirrors.tuna.tsinghua.edu.cn
RUN sed -i "s|http://deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources && \
    apt-get -o Acquire::http::Timeout=30 -o Acquire::Retries=2 update && \
    apt-get install -y --no-install-recommends bash bubblewrap ca-certificates curl git gh openssh-client tini procps python3 ripgrep tmux libatomic1 libstdc++6 && \
    rm -rf /var/lib/apt/lists/*
# ASVS 1.2.5: quoted arguments; pinned official artifact is verified before extraction.
COPY .cache/orca-server-linux-x64.tar.gz /tmp/orca.tar.gz
RUN echo "${ORCA_SHA256}  /tmp/orca.tar.gz" | sha256sum -c - && \
    mkdir /opt/orca && \
    tar -xzf /tmp/orca.tar.gz -C /opt/orca --strip-components=1 && \
    rm /tmp/orca.tar.gz && \
    grep -Fx "orca ${ORCA_VERSION}" /opt/orca/VERSION && \
    ln -s /opt/orca/bin/orca-ide /usr/local/bin/orca
COPY scripts/entrypoint.sh /usr/local/bin/orca-entrypoint
COPY scripts/agent.sh /usr/local/bin/orca-agent
RUN chmod 755 /usr/local/bin/orca-entrypoint /usr/local/bin/orca-agent
RUN useradd --uid 1026 --gid 100 --home-dir /data/home --no-create-home --shell /bin/bash orca
ENV NODE_USE_ENV_PROXY=1 \
    NPM_CONFIG_NOPROXY=registry.npmjs.org \
    HOME=/data/home \
    ORCA_USER_DATA_PATH=/data/profile \
    NPM_CONFIG_PREFIX=/data/agents \
    PATH=/data/agents/bin:/usr/local/bin:/usr/bin:/bin \
    LANG=C.UTF-8 \
    TZ=Asia/Shanghai
WORKDIR /workspace
USER 1026:100
ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/usr/local/bin/orca-entrypoint"]
