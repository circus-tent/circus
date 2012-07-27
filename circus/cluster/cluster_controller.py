import circus.controller

class ClusterController(Controller):
    def handle_message(self, raw_msg):
        print 'received!'
        print raw_msg
