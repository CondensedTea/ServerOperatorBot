class Text:
    welcome = "Добро пожаловать, вы были успешно зарегистрированны в системе"
    broken_link = "Эта ссылка больше не работает, обратитесь к администратору за новой ссылкой для регистрации"
    user_in_base = "Вы уже зарегестрированы в системе"
    open_server_error = "Сейчас невозможно создать сервер, обратитесь в поддержку helpdesk@rtdprk.ru"

    def __init__(self, name=None):
        self.n = name

    def creation_complete(self):
        return 'Ваша заявка успешно принята, сервер cloud-pc-{}.hq.rtdprk.ru будет доступен через 10 минут'.format(self.n)

    def user_have_server(self):
        return 'Вы уже создали сервер cloud-pc-{}, что бы открыть новый сервер, необходимо его закрыть командой /close'.format(self.n)

    def deletion_complete(self):
        return 'Вы успешно закрыли сервер cloud-pc-{}'.format(self.n)

    def deletion_error(self):
        return 'Не удалось закрыть сервер сloud-pc-{}, обратитесь в поддержку helpdesk@rtdprk.ru'.format(self.n)
