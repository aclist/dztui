DZG_006 = """The leading cause of specific servers periodically timing out is local network configuration.

Many third-party DayZ servers use a server rental/hosting provider with DDoS protection.

This can cause responses from servers to originate from a server other than the one originally queried.

Consumer-grade routers are likely to drop this traffic as invalid due to how they handle NAT (network address translation).

By contrast, wireless routers and enterprise-grade routers may be less likely to have this issue.

If you find that a specific server is unresponsive for you when it shouldn't be, add a port forwarding rule to your router's settings for the server's query port.

In addition, packets received from server responses are expected to be a standard size: MTU (maximum transmission unit) of 1500.

Deviation from this may cause your router to discard incoming responses from the server."""
