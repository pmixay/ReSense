import { Button, Card, EmptyState, PageHeader } from '../../components';

export default function NotFound() {
  return (
    <>
      <PageHeader title="Не найдено" station="warning" />
      <Card>
        <EmptyState
          icon="warning"
          title="Такой страницы нет"
          action={
            <Button variant="dark" icon="home" to="/">
              На главную
            </Button>
          }
        >
          Проверьте адрес или вернитесь на главную.
        </EmptyState>
      </Card>
    </>
  );
}
