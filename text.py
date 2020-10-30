class Text:
    welcome = "Добро пожаловать, вы были успешно зарегистрированны в системе"
    broken_link = "Эта ссылка больше не работает, обратитесь к администратору за новой ссылкой для регистрации"
    user_in_base = "Вы уже зарегестрированы в системе"
    open_server_error = "Сейчас невозможно создать сервер, обратитесь в поддержку helpdesk@rtdprk.ru"

    def __init__(self, ip=None):
        self.i = ip

    def creation_complete(self):
        return 'Ваша заявка успешно принята, сервер Cloud-PC-{}.hq.rtdprk.ru будет доступен через 10 минут'.format(self.i)

    def user_have_server(self):
        return 'Вы уже создали сервер Cloud-PC-{}, что бы открыть новый сервер, необходимо его закрыть командой /close'.format(self.i)

    def deletion_complete(self):
        return 'Вы успешно закрыли сервер Cloud-PC-{}'.format(self.i)

    def deletion_error(self):
        return 'Не удалось закрыть сервер Cloud-PC-{}, обратитесь в поддержку helpdesk@rtdprk.ru'.format(self.i)
