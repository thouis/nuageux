from twisted.web import server, resource
from twisted.internet import reactor

class Simple(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        print request, str(request)
        return "<html>Hello, world!<p>'%s'</html>"%(str(request))

site = server.Site(Simple())
reactor.listenTCP(8080, site)
reactor.run()
