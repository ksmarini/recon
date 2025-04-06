FROM kalilinux/kali-rolling

# 1. Configurações de Ambiente Essenciais
ENV TERM=xterm-256color \
    GOPATH=/go \
    GOBIN=/go/bin \
    PATH="/usr/local/go/bin:/go/bin:${PATH}" \
    CGO_ENABLED=1

# 2. Cria diretórios essenciais (sem /go)
RUN mkdir -p /data /scripts
WORKDIR /scripts

# 3. Atualizações e instalação de pacotes
RUN apt-get update -qq && \
    apt-get full-upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        wget \
        git \
        vim \
        dnsutils \
        python3 \
        python3-pip \
        nmap \
        nikto \
        hydra \
        locate \
        libpcap-dev \
        build-essential \
        libssl-dev \
        python3-dnspython \
        python3-requests \
        libffi-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4. Instalação do Go
RUN cd /tmp && \
    wget -q https://go.dev/dl/go1.24.2.linux-amd64.tar.gz && \
    tar -xzf go1.24.2.linux-amd64.tar.gz -C /usr/local && \
    rm go1.24.2.linux-amd64.tar.gz

# 5. Instalação das ferramentas Go (cria /go automaticamente)
RUN mkdir -p ${GOPATH}/bin && \
    go install -v -mod=mod github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest && \
    go install -v -mod=mod github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest && \
    go install -v -mod=mod github.com/tomnomnom/assetfinder@latest && \
    go install -v -mod=mod github.com/openrdap/rdap/cmd/rdap@master && \
    go install -v -mod=mod github.com/projectdiscovery/httpx/cmd/httpx@latest && \
    go install -v -mod=mod github.com/tomnomnom/waybackurls@latest
    # go install -v \
    # github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest \
    # github.com/tomnomnom/assetfinder@latest \
    # github.com/openrdap/rdap/cmd/rdap@master \
    # github.com/projectdiscovery/httpx/cmd/httpx@latest \
    # github.com/tomnomnom/waybackurls@latest \
    # github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# 6. Pós-instalação e ajustes finais
RUN nuclei -update-templates && \
    git clone https://github.com/aboul3la/Sublist3r.git && \
    updatedb && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    chmod -R 755 /go
