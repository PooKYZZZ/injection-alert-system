FROM owasp/modsecurity-crs@sha256:0385a81159d5112c113eeeed01c3f6cf05113891b02addc23abeab180934911e

USER root
RUN apk add --no-cache python3 py3-pip \
    && python3 -m pip install --no-cache-dir --break-system-packages \
        httpx==0.28.1
COPY waf_runtime /opt/pr7/waf_runtime
COPY config/modsecurity/setup.conf.template /etc/nginx/templates/modsecurity.d/setup.conf.template
COPY config/modsecurity/pr7-runtime-include.conf.template /etc/nginx/templates/modsecurity.d/pr7-runtime-include.conf.template
COPY config/modsecurity/pr7-probe.conf.template /etc/nginx/templates/conf.d/pr7-probe.conf.template
RUN mkdir -p /pr7-state /var/log/modsecurity /var/log/modsecurity/audit \
    && chown -R nginx:nginx /opt/pr7 /pr7-state /var/log/modsecurity
COPY docker/pr7-waf-entrypoint.sh /usr/local/bin/pr7-waf-entrypoint
COPY docker/pr7-waf-control /usr/local/bin/pr7-waf-control
COPY docker/pr7-waf-smoke.py /opt/pr7/pr7-waf-smoke.py
RUN chmod 0755 /usr/local/bin/pr7-waf-entrypoint /usr/local/bin/pr7-waf-control
ENV PYTHONPATH=/opt/pr7
ENV PR7_PROBE_PORT=8081
USER nginx
ENTRYPOINT ["/usr/local/bin/pr7-waf-entrypoint"]
CMD []
