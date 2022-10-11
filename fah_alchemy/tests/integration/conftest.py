"""Components for standing up services for integration tests, including databases.

"""
from os import getenv

from grolt import Neo4jService, Neo4jDirectorySpec
from grolt.security import install_self_signed_certificate
from pytest import fixture

from py2neo import ServiceProfile, Graph
from py2neo.client import Connector


NEO4J_PROCESS = {}
NEO4J_VERSION = getenv("NEO4J_VERSION", "")


UNSECURED_SCHEMES = ["neo4j", "bolt", "http"]
ALL_SCHEMES = ["neo4j", "neo4j+s", "neo4j+ssc",
               "bolt", "bolt+s", "bolt+ssc",
               "http", "https", "http+s", "http+ssc"]
SSC_SCHEMES = ["neo4j", "neo4j+ssc", "bolt", "bolt+ssc", "http", "http+ssc"]

UNSECURED_LEGACY_SCHEMES = ["bolt", "http"]
ALL_LEGACY_SCHEMES = ["bolt", "bolt+s", "bolt+ssc", "http", "https", "http+s", "http+ssc"]
SSC_LEGACY_SCHEMES = ["bolt", "bolt+ssc", "http", "http+ssc"]


class DeploymentProfile(object):

    def __init__(self, release=None, topology=None, cert=None, schemes=None):
        self.release = release
        self.topology = topology   # "CE|EE-SI|EE-C3|EE-C3-R2"
        self.cert = cert
        self.schemes = schemes

    def __str__(self):
        server = "%s.%s %s" % (self.release[0], self.release[1], self.topology)
        if self.cert:
            server += " %s" % (self.cert,)
        schemes = " ".join(self.schemes)
        return "[%s]-[%s]" % (server, schemes)


class TestProfile:

    def __init__(self, deployment_profile=None, scheme=None):
        self.deployment_profile = deployment_profile
        self.scheme = scheme
        assert self.topology == "CE"

    def __str__(self):
        extra = "%s" % (self.topology,)
        if self.cert:
            extra += "; %s" % (self.cert,)
        bits = [
            "Neo4j/%s.%s (%s)" % (self.release[0], self.release[1], extra),
            "over",
            "'%s'" % self.scheme,
        ]
        return " ".join(bits)

    @property
    def release(self):
        return self.deployment_profile.release

    @property
    def topology(self):
        return self.deployment_profile.topology

    @property
    def cert(self):
        return self.deployment_profile.cert

    @property
    def release_str(self):
        return ".".join(map(str, self.release))

    def generate_uri(self, service_name=None):
        if self.cert == "full":
            raise NotImplementedError("Full certificates are not yet supported")
        elif self.cert == "ssc":
            certificates_dir = install_self_signed_certificate(self.release_str)
            dir_spec = Neo4jDirectorySpec(certificates_dir=certificates_dir)
        else:
            dir_spec = None
        with Neo4jService(name=service_name, image=self.release_str,
                          auth=("neo4j", "password"), dir_spec=dir_spec) as service:
            uris = [router.uri(self.scheme) for router in service.routers()]
            yield service, uris[0]


# TODO: test with full certificates
neo4j_deployment_profiles = [
    DeploymentProfile(release=(4, 4), topology="CE", schemes=UNSECURED_SCHEMES),
    DeploymentProfile(release=(4, 4), topology="CE", cert="ssc", schemes=SSC_SCHEMES),
]

if NEO4J_VERSION == "LATEST":
    neo4j_deployment_profiles = neo4j_deployment_profiles[:1]
elif NEO4J_VERSION == "4.x":
    neo4j_deployment_profiles = [profile for profile in neo4j_deployment_profiles
                                 if profile.release[0] == 4]
elif NEO4J_VERSION == "4.4":
    neo4j_deployment_profiles = [profile for profile in neo4j_deployment_profiles
                                 if profile.release == (4, 4)]


neo4j_test_profiles = [TestProfile(deployment_profile, scheme=scheme)
                       for deployment_profile in neo4j_deployment_profiles
                       for scheme in deployment_profile.schemes]

@fixture(scope="session",
         params=neo4j_test_profiles,
         ids=list(map(str, neo4j_test_profiles)))
def test_profile(request):
    test_profile = request.param
    yield test_profile


@fixture(scope="session")
def neo4j_service_and_uri(test_profile):
    for service, uri in test_profile.generate_uri("py2neo"):
        yield service, uri
    return


@fixture(scope="session")
def uri(neo4j_service_and_uri):
    _, uri = neo4j_service_and_uri
    return uri


@fixture(scope="session")
def graph(uri):
    return Graph(uri)